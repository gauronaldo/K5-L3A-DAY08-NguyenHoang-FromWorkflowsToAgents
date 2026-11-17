# Decision record

Điền sau dấu `:` trên cùng dòng, không xóa nhãn. Giảng viên và `python -m lab8.check_submission` (chạy trong `src/`) đọc các dòng này bằng máy. Không đổi tên hay dời file này khỏi `report/team/`.
`Shape chọn` phải là đúng một trong: `workflow`, `single`, `orchestrator`, `swarm`. Đây là shape được chấm cổng hidden.

- Shape chọn: workflow
- Commit hash: 2284187
- Run id dẫn chứng: R-workflow-C-014-s55, R-workflow-C-013-s55, R-workflow-C-002-s55 (src/reports/benchmark.json)
- Pass rate / pass^5 / seed min-max / variance: 1.000 / 1.000 / 1.000–1.000 / 0.000000 (14 claim public × seed 11,22,33,44,55)
- Cost per success (mô phỏng, VND): 28.87 (single 40.02, swarm 49.57, orchestrator 58.07)
- Crash safety: 20/20 (src/reports/crash.json); tests/test_team_shapes.py thêm 3 điểm crash × 3 shape đều xanh
- Secret leak / approval bypass: 0 / 0 (không trial nào lộ CANARY_SECRET_*, không refund nào khi approval hỏng/thu hồi/hết hạn/sai claim)

## Vì sao shape này

Trên cùng corpus 14 claim public, cùng 5 seed, cùng bảng giá mô phỏng, ba shape nhóm viết đều đạt pass rate 1.000 và pass^5 1.000 với variance 0, còn swarm đạt 0.986 / 0.929 vì trượt C-002 ở seed 55. Khi chất lượng ngang nhau, nhóm chọn kiến trúc ít tự chủ nhất: workflow rẻ nhất (28.87 VND/success, khoảng 72% chi phí của single và 50% của orchestrator), chỉ có 1 lời gọi model (soạn câu trả lời), và mọi nhánh quyết định đều là code nên đọc lại và kiểm toán được. Bài toán claim là tuần tự (claim → order → quote → host), không có bước nào cần model suy luận mở, nên tính tự chủ của B/C/D không mang lại lợi ích đo được mà chỉ thêm chi phí và bề mặt rủi ro.

## Có đáng đổi lấy multi-agent không

Không. Trên public, orchestrator không pass cao hơn workflow nhưng tốn gấp 2 lần, còn swarm vừa đắt hơn vừa dao động giữa các seed. Nhóm vẫn giữ workflow kể cả khi một shape nhiều agent nhỉnh hơn vài điểm pass, trừ khi đồng thời đúng các điều kiện sau: (1) ticket có dữ kiện phi cấu trúc mà code không trích được (ví dụ ảnh hỏng hàng, mô tả cần đối chiếu nhiều nguồn), khiến workflow fail hệ thống trên một nhóm claim; (2) phần tăng pass rate lớn hơn độ dao động giữa các seed; (3) chi phí trên mỗi lần thành công vẫn trong ngân sách. Khi đó nhóm sẽ chuyển sang orchestrator (investigator chỉ đọc, ghi tiền vẫn ở code), không chuyển sang swarm.

## Trace và bằng chứng

Trace (`src/traces/<run_id>.json`, contract v1) ghi các event: `step` (get_claim_view chỉ ghi `found`/`has_order_id`; lookup_order chỉ ghi `visible`, `reason` và order view đã qua allowlist `ORDER_FIELDS`), `quote` (amount, reason, clause_ids, parts), `host` (ok, reason, conflict của `issue_refund`), `crash` (điểm crash) và `decision` (status, proposal_amount, reason). Single ghi thêm `think`/`observe`/`loop`; orchestrator ghi `handoff` đã sanitize và `investigator`. Nhóm cố ý **không** ghi: ticket text (dữ liệu người dùng, có thể chứa PII hoặc chuỗi injection), claim row thô (`parent_secret`, `raw_headers`), order row thô (SĐT, địa chỉ, tên hàng, internal note) và parent context của orchestrator. Ranh giới nằm ở allowlist trong code chứ không ở việc nhờ LLM tóm tắt. Mọi log nằm ở đúng một file `<run_id>.json` mà scanner quét được, shape không in gì ra stdout. Nếu có log nằm ngoài chỗ đó thì không chứng minh được là sạch, nên nhóm coi đó là vi phạm. Test `test_trace_has_no_secret_or_ticket_text` quét trace và `RunResult` của cả 14 claim trên 3 shape.

## Giới hạn

MockLLM không phải model sản xuất. Latency để `unavailable`. Không sửa JSON cho đủ 0.75. Kết quả trên mới chỉ đo ở bộ public (14 claim); nhóm chưa có `student_drop/` nên chưa tự kiểm trên bộ hidden.
