"""Shape C — orchestrator plus read-only investigators.

1. Orchestrator reads the claim view and plans (one MockLLM call).
2. It builds a handoff with `lab8.handoff.make_handoff`: allowlisted fields,
   read-only tools only, empty facts (no parent_secret, no headers, no claim row).
3. `lab8.runtime.run_readonly_investigators` runs those tools. Investigators
   have no write registry.
4. Orchestrator (code) quotes from the investigator's order view and is the
   only caller of `durability.issue_refund`. FULL quote; the host subtracts
   earlier refunds on the same order.
5. Trace stores the sanitized handoff, never the parent context.

An LLM summary of the parent context is not a sanitizer; the allowlist is.
"""

from __future__ import annotations

import sqlite3

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.handoff import HandoffError, make_handoff
from lab8.mock_llm import complete
from lab8.runtime import ToolRejected, run_readonly_investigators
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.tools import get_claim_view, tool_cost
from lab8.trace import Trace

SHAPE = "orchestrator"
INVESTIGATOR_TOOLS = ["lookup_order", "lookup_refund_history", "lookup_policy", "compute_compensation"]


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

    # Orchestrator: read the claim view and plan.
    budget.add_tool(tool_cost())
    claim = get_claim_view(conn, claim_id)
    trace.add("orchestrator", {"step": "claim_view", "found": claim["found"], "has_order_id": bool(claim.get("order_id"))})
    if not claim["found"]:
        return done("failed", 0, "unknown_claim")
    complete(budget, seed=seed, purpose="plan", prompt=f"claim={claim_id} tools={INVESTIGATOR_TOOLS}")
    if not claim.get("order_id"):
        return done("needs_info", 0, "missing_order_id")

    # Handoff across the trust boundary: allowlist only, read-only tools only.
    try:
        handoff = make_handoff(
            request_id=f"REQ-{claim_id}",
            claim_id=claim_id,
            task="investigate_refund_eligibility",
            facts={},
            allowed_tools=INVESTIGATOR_TOOLS,
        )
        investigated = run_readonly_investigators(conn, budget, handoff, principal_id=claim["principal_id"])
    except (HandoffError, ToolRejected) as exc:
        trace.add("error", {"reason": "handoff_rejected", "detail": str(exc)})
        return done("failed", 0, "handoff_rejected")
    trace.add("handoff", safe_dump(handoff))
    complete(budget, seed=seed, purpose="investigate", prompt=f"handoff={handoff['request_id']}")

    tools = investigated["tools"]
    order_view = tools.get("lookup_order") or {}
    history = tools.get("lookup_refund_history") or {}
    trace.add(
        "investigator",
        {
            "visible": bool(order_view.get("visible")),
            "reason": order_view.get("reason"),
            "order": safe_dump(order_view["order"]) if order_view.get("visible") else None,
            "refunded_vnd": history.get("refunded_vnd"),
            "policy_count": len((tools.get("lookup_policy") or {}).get("policies") or []),
        },
    )
    if not order_view.get("visible"):
        return done("escalated", 0, order_view.get("reason"))

    quote = tools.get("compute_compensation")
    if quote is None:
        return done("failed", 0, "no_quote")
    trace.add("quote", safe_dump(quote))
    proposal = int(quote["amount_vnd"])
    if proposal <= 0:
        return done("denied", 0, quote.get("reason"))

    # Only the orchestrator writes, and only through the host gate.
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
