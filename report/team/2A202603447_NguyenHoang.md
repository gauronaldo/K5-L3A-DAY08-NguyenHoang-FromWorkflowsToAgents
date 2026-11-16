# Báo cáo cá nhân — 2A202603447_NguyenHoang

## 1. Thông tin thành viên

- Họ tên: Nguyễn Hoàng
- MSSV: 2A202603447
- Email: hoangng1304@gmail.com
- GitHub: gauronaldo

## 2. Phần việc phụ trách

Shape `workflow` và `single`, kiểm crash/idempotency (crash suite, T11, T12), viết báo cáo nhóm `group_report.md`.

## 3. Đóng góp cụ thể

- Commit `feat: shape workflow + single, crash tests, group report (Nguyen Hoang)`: cài `src/lab8/shapes/workflow.py` và `src/lab8/shapes/single.py`, sinh `src/reports/crash.json`.
- Test: `src/tests/test_team_shapes.py` (13 test) gồm crash ở 3 điểm (`before_effect`, `after_effect_before_checkpoint`, `after_checkpoint`) × 3 shape rồi resume, claim không tồn tại, và giới hạn 8 bước của single.
- Quyết định kỹ thuật:
  - Workflow chạy theo bước cố định và chỉ gọi model 1 lần để soạn câu trả lời.
  - Single: model chỉ chọn tool đọc trong `run_react` (`worker=True`). Sau vòng lặp, code đọc lại quote từ kết quả tool, không dùng `final` do model trả.
  - Truyền quote **đầy đủ** vào `issue_refund` để host tự trừ phần đã hoàn (T13, T14).
  - Không bắt `InjectedCrash`. Trước khi re-raise thì flush trace để vẫn còn bằng chứng.

## 4. Bằng chứng

- `pytest -q -m student -o addopts= -k "workflow or single"`: pass hết. `pytest -q`: 110 passed (54 test cổng host + 56 test nhóm).
- `tests/test_team_shapes.py`: 13 passed.
- `src/reports/crash.json`: `crash_safety` 20/20.
- `report/team/group_report.md`: bảng so sánh 4 shape, phân công, khó khăn và cách xử lý.

## 5. Công cụ AI

- Có dùng trợ lý AI để hỗ trợ viết code và báo cáo; tự kiểm tra bằng `pytest`, `crash_test` và `check_submission` (0 FAIL).
