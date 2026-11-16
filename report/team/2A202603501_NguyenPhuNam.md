# Báo cáo cá nhân — 2A202603501_NguyenPhuNam

## 1. Thông tin thành viên

- Họ tên: Nguyễn Phú Nam
- MSSV: 2A202603501
- Email: phunam402@gmail.com
- GitHub: Manny402

## 2. Phần việc phụ trách

Shape `orchestrator` và handoff, kiểm ranh giới bảo mật của trace, chạy benchmark 4 shape × 5 seed, ablation R2, viết `decision_adr.md` (chọn workflow dựa trên benchmark) và `research_card.md`.

## 3. Đóng góp cụ thể

- Commit `feat: shape orchestrator + handoff, security tests, benchmark, ADR, research card (Nguyen Phu Nam)`.
- Code: `src/lab8/shapes/orchestrator.py`. Orchestrator đọc claim view, dựng handoff bằng `make_handoff` với `facts={}` và chỉ tool đọc (`lookup_order`, `lookup_refund_history`, `lookup_policy`, `compute_compensation`). Investigator chạy qua `run_readonly_investigators`. Chỉ orchestrator gọi `issue_refund` với quote đầy đủ.
- Test: `src/tests/test_team_security.py` (43 test) kiểm tra trace và `RunResult` không lộ `CANARY_SECRET_*`, `parent_secret` hay ticket text trên 14 claim × 3 shape, worker không gọi được `issue_refund`, và handoff không cấp được write tool.
- Benchmark và ablation: sinh `src/reports/benchmark.json` và `src/reports/ablation_r2_seed55.json`. Phân loại lỗi của swarm ở C-002 seed 55 theo MAST (nhóm task verification).
- Quyết định kỹ thuật: trace chỉ ghi handoff đã sanitize và view đã qua allowlist; không ghi parent context, claim row hay order row thô. Tóm tắt bằng LLM không được coi là redaction.

## 4. Bằng chứng

- `pytest -q -m student -o addopts= -k orchestrator`: 62 passed.
- `tests/test_team_security.py`: 43 passed.
- `src/reports/benchmark.json`: orchestrator 1.000 / pass^5 1.000 / 58.07 VND/success; swarm 0.986 / 0.929.
- Ablation R2: `R-swarm-C-002-s55` fail, `R-orchestrator-C-002-s55` pass.

## 5. Công cụ AI

- Có dùng trợ lý AI để hỗ trợ viết code và báo cáo; tự kiểm tra bằng `pytest` và `check_submission`.
