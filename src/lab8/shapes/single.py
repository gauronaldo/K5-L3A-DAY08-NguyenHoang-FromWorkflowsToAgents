"""Shape B — one ReAct agent.

`lab8.runtime.run_react` drives a bounded loop (max_steps=8). Each step the
"model" (MockLLM, seeded) looks at what it has seen so far and picks a READ
tool: get_claim_view -> lookup_order -> lookup_refund_history ->
compute_compensation, then returns a final proposal.

What the model is NOT allowed to do:
- choose the money: the amount comes from the `compute_compensation` tool
  result, which code re-reads after the loop;
- trust the ticket: the delay/clause written in the ticket is never fed into
  the quote, only the order row is;
- commit: `issue_refund` is a write tool, `dispatch` refuses it. After the loop
  the shape (code) validates and calls `durability.issue_refund` with the FULL
  quote; the host subtracts earlier refunds on the same order (T13, T14).

Trace contract v1: every return path writes `traces/<run_id>.json` with only
allowlisted views (no ticket text, no raw claim/order row).
"""

from __future__ import annotations

import sqlite3
from typing import Any

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.mock_llm import complete
from lab8.runtime import ToolRejected, run_react
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.trace import Trace

SHAPE = "single"
MAX_STEPS = 8


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()


def _run(conn: sqlite3.Connection, claim_id: str, *, seed: int, crash_at: str | None) -> RunResult:
    budget = Budget()
    trace = Trace(make_run_id(SHAPE, claim_id, seed))
    # Facts collected from tool results. Code reads these after the loop;
    # the model's own final text is never used for money or status.
    seen: dict[str, Any] = {}

    def done(status: str, proposal: int, reason: str | None) -> RunResult:
        complete(budget, seed=seed, purpose="draft", prompt=f"status={status} proposal={proposal}")
        trace.add("decision", {"status": status, "proposal_amount": int(proposal), "reason": reason})
        return finish(
            conn,
            shape=SHAPE,
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=reason,
        )

    def record(obs: dict[str, Any]) -> None:
        tool = obs.get("last_tool")
        if tool:
            seen[tool] = obs.get("last_result") or {}
            trace.add("observe", _trace_view(tool, seen[tool]))

    def decide(obs: dict[str, Any]) -> dict[str, Any]:
        record(obs)
        step = len([e for e in trace.events if e["kind"] == "think"])
        # One model call per ReAct step so cost is comparable across shapes.
        complete(budget, seed=seed, purpose="react", prompt=f"step={step} seen={sorted(seen)}")
        trace.add("think", {"step": step, "seen": sorted(seen)})

        claim = seen.get("get_claim_view")
        if claim is None:
            return {"tool": "get_claim_view", "args": {"claim_id": claim_id}}
        if not claim.get("found"):
            return {"final": {"status": "failed", "reason": "unknown_claim"}}
        if not claim.get("order_id"):
            return {"final": {"status": "needs_info", "reason": "missing_order_id"}}
        scope = {"order_id": claim["order_id"], "principal_id": claim["principal_id"]}
        if "lookup_order" not in seen:
            return {"tool": "lookup_order", "args": scope}
        order_view = seen["lookup_order"]
        if not order_view.get("visible"):
            return {"final": {"status": "escalated", "reason": order_view.get("reason")}}
        if "lookup_refund_history" not in seen:
            return {"tool": "lookup_refund_history", "args": scope}
        if "compute_compensation" not in seen:
            # Quote from the order row, never from ticket text.
            return {"tool": "compute_compensation", "args": {"order": order_view["order"]}}
        return {"final": {"status": "propose", "amount_vnd": seen["compute_compensation"].get("amount_vnd")}}

    try:
        loop = run_react(
            conn,
            budget,
            observation={"claim_id": claim_id},
            decide=decide,
            max_steps=MAX_STEPS,
            worker=True,
        )
    except ToolRejected as exc:
        trace.add("error", {"reason": "tool_rejected", "detail": str(exc)})
        return done("failed", 0, "tool_rejected")

    final = loop["final"]
    trace.add("loop", {"stopped": loop["stopped"], "final_status": final.get("status")})
    if loop["stopped"] != "final":
        return done("failed", 0, "step_cap")

    # ---- Code takes over: validate, then commit through the host. ----
    claim = seen.get("get_claim_view") or {}
    if not claim.get("found"):
        return done("failed", 0, "unknown_claim")
    if not claim.get("order_id"):
        return done("needs_info", 0, "missing_order_id")
    order_view = seen.get("lookup_order") or {}
    if not order_view.get("visible"):
        return done("escalated", 0, order_view.get("reason"))
    quote = seen.get("compute_compensation")
    if quote is None:
        return done("failed", 0, "no_quote")

    proposal = int(quote["amount_vnd"])  # from the tool, not from the model's final
    if proposal <= 0:
        return done("denied", 0, quote.get("reason"))

    try:
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise
    trace.add("host", {"ok": outcome["ok"], "reason": outcome["reason"], "conflict": outcome["conflict"]})
    if not outcome["ok"]:
        return done("failed" if outcome["conflict"] else "denied", proposal, outcome["reason"])
    return done("resolved", proposal, None)


def _trace_view(tool: str, result: dict[str, Any]) -> dict[str, Any]:
    """Allowlisted summary of a tool result. Ticket text never reaches the trace."""
    if tool == "get_claim_view":
        return {"tool": tool, "found": bool(result.get("found")), "has_order_id": bool(result.get("order_id"))}
    if tool == "lookup_order":
        view = {"tool": tool, "visible": bool(result.get("visible")), "reason": result.get("reason")}
        if result.get("visible"):
            view["order"] = safe_dump(result["order"])
        return view
    if tool == "lookup_refund_history":
        return {
            "tool": tool,
            "visible": bool(result.get("visible")),
            "refund_count": result.get("refund_count"),
            "refunded_vnd": result.get("refunded_vnd"),
        }
    if tool == "compute_compensation":
        return {"tool": tool, **safe_dump(result)}
    return {"tool": tool}
