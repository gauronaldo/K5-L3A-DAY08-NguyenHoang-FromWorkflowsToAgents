"""Team tests (Nguyễn Hoàng): durability and control flow of the student shapes.

- every crash point, then resume -> exactly one refund and one committed audit;
- unknown claim -> clean `failed` with a trace, no exception;
- the single agent stays within its 8-step ReAct cap.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lab8.db import connect, init_store
from lab8.durability import InjectedCrash, committed_audit_count, get_refund
from lab8.shapes import SHAPES
from tests.conftest import CLAIMS, WORLD

TEAM_SHAPES = ["workflow", "single", "orchestrator"]
CRASH_POINTS = ["before_effect", "after_effect_before_checkpoint", "after_checkpoint"]


def _store(tmp_path: Path, name: str) -> str:
    path = tmp_path / name
    init_store(path, WORLD, CLAIMS).close()
    return str(path)


@pytest.mark.parametrize("shape", TEAM_SHAPES)
@pytest.mark.parametrize("point", CRASH_POINTS)
def test_crash_then_resume_pays_once(tmp_path, shape, point):
    store = _store(tmp_path, f"{shape}-{point}.sqlite")
    with pytest.raises(InjectedCrash):
        SHAPES[shape]("C-001", seed=11, store_path=store, crash_at=point)
    result = SHAPES[shape]("C-001", seed=11, store_path=store)
    assert result.status == "resolved"
    assert result.proposal_amount == 35000
    conn = connect(store)
    try:
        assert int(get_refund(conn, "C-001")["amount_vnd"]) == 35000
        assert committed_audit_count(conn, "C-001") == 1
        rows = conn.execute("SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id = 'C-001'").fetchone()["n"]
        assert rows == 1
    finally:
        conn.close()


@pytest.mark.parametrize("shape", TEAM_SHAPES)
def test_unknown_claim_fails_cleanly(tmp_path, shape):
    store = _store(tmp_path, f"{shape}-unknown.sqlite")
    result = SHAPES[shape]("C-DOES-NOT-EXIST", seed=11, store_path=store)
    assert result.status == "failed"
    assert result.proposal_amount == 0
    assert result.refund_effects == []
    assert Path(result.trace_path).exists()


def test_single_agent_respects_step_cap(tmp_path):
    store = _store(tmp_path, "single-steps.sqlite")
    result = SHAPES["single"]("C-001", seed=11, store_path=store)
    body = json.loads(Path(result.trace_path).read_text(encoding="utf-8"))
    thinks = [e for e in body["events"] if e["kind"] == "think"]
    assert 1 <= len(thinks) <= 8
