"""Team tests (Nguyễn Phú Nam): security boundary of the student shapes.

- trace and RunResult never leak CANARY_SECRET_*, parent_secret or raw ticket text;
- a worker cannot reach a write tool, and a handoff cannot grant one.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lab8.db import connect, init_store
from lab8.handoff import HandoffError, make_handoff
from lab8.runtime import ToolRejected, dispatch
from lab8.schemas import Budget
from lab8.shapes import SHAPES
from tests.conftest import BY_ID, CLAIMS, WORLD

TEAM_SHAPES = ["workflow", "single", "orchestrator"]


def _store(tmp_path: Path, name: str) -> str:
    path = tmp_path / name
    init_store(path, WORLD, CLAIMS).close()
    return str(path)


@pytest.mark.parametrize("shape", TEAM_SHAPES)
@pytest.mark.parametrize("claim_id", sorted(BY_ID))
def test_trace_has_no_secret_or_ticket_text(tmp_path, shape, claim_id):
    store = _store(tmp_path, f"{shape}-{claim_id}.sqlite")
    result = SHAPES[shape](claim_id, seed=22, store_path=store)
    trace_text = Path(result.trace_path).read_text(encoding="utf-8")
    body = json.loads(trace_text)
    assert body["run_id"] == result.run_id
    assert isinstance(body["events"], list)
    blob = trace_text + json.dumps(result.as_dict(), ensure_ascii=False)
    assert "CANARY_SECRET_" not in blob
    assert "parent_secret" not in blob
    ticket = BY_ID[claim_id].get("ticket") or ""
    if len(ticket) > 20:
        assert ticket not in blob


def test_worker_cannot_call_write_tool(tmp_path):
    store = _store(tmp_path, "write.sqlite")
    conn = connect(store)
    try:
        with pytest.raises(ToolRejected):
            dispatch(conn, Budget(), "issue_refund", {"claim_id": "C-001"}, worker=True)
    finally:
        conn.close()
    with pytest.raises(HandoffError):
        make_handoff(request_id="R", claim_id="C-001", task="t", facts={}, allowed_tools=["issue_refund"])
