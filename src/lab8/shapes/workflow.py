"""Shape A — deterministic workflow.

Signature (do not change):

    run_claim(claim_id, *, seed, store_path, crash_at=None) -> RunResult

Fixed Python steps. Money stays in code (`lab8.tools.compute_compensation`).
The model is only used once, to draft the reply text; it never sees money
decisions and never commits anything.

1. Read the claim through `get_claim_view` (allowlisted columns, not SELECT *).
2. Missing order_id -> `needs_info`. No ledger write.
3. `lookup_order` scoped to the claim's principal. Not visible -> `escalated`.
4. Quote from the order row only. Ticket text is user data, never trusted.
5. Quote 0 -> `denied`, no issue_refund.
6. Quote > 0 -> `durability.issue_refund(conn, claim_id, <full quote>, crash_at=...)`.
   Host rejects -> `denied` (host writes `policy_denied`); conflict -> `failed`.
7. Success -> `resolved` with proposal_amount = full quote.

Trace: only allowlisted views are traced (no ticket text, no claim/order row).
"""

from __future__ import annotations

import sqlite3

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.mock_llm import complete
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.tools import compute_compensation, get_claim_view, lookup_order, tool_cost
from lab8.trace import Trace

SHAPE = "workflow"


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

    # Step 1: claim view (allowlisted columns).
    budget.add_tool(tool_cost())
    claim = get_claim_view(conn, claim_id)
    trace.add("step", {"name": "get_claim_view", "found": claim["found"], "has_order_id": bool(claim.get("order_id"))})
    if not claim["found"]:
        return done("failed", 0, "unknown_claim")

    # Step 2: never recover an order id from ticket text.
    if not claim.get("order_id"):
        return done("needs_info", 0, "missing_order_id")

    # Step 3: order scoped to the claim's principal.
    budget.add_tool(tool_cost())
    order_view = lookup_order(conn, claim["order_id"], claim["principal_id"])
    if not order_view["visible"]:
        trace.add("step", {"name": "lookup_order", "visible": False, "reason": order_view["reason"]})
        return done("escalated", 0, order_view["reason"])
    trace.add("step", {"name": "lookup_order", "visible": True, "order": safe_dump(order_view["order"])})

    # Step 4: quote in code from the DB row.
    budget.add_tool(tool_cost())
    quote = compute_compensation(conn, order_view["order"])
    trace.add("quote", safe_dump(quote))
    proposal = int(quote["amount_vnd"])

    # Step 5: nothing to pay.
    if proposal <= 0:
        return done("denied", 0, quote.get("reason"))

    # Step 6: host gate is the only writer. Full quote, crash_at passed through.
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
