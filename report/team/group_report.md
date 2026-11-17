# Báo cáo nhóm — Lab 8 LogiX-VN

Tối đa 5 trang ngoài phụ lục. Số liệu lấy từ file trong `src/reports/`, không chép tay từ terminal.

## 1. Thông tin nhóm

- Tên nhóm: NguyenHoang
- Thành viên: xem `TEAM.md`
- Commit chốt: ghi trong `report/team/decision_adr.md`

## 2. Mục tiêu và cách tiếp cận

Bài toán: xử lý claim hoàn phí vận chuyển theo 4 kiến trúc có cùng chữ ký `run_claim`, rồi chọn kiến trúc ít tự chủ nhất mà vẫn làm được việc. Nhóm thống nhất ba ranh giới trước khi viết code:

1. **Tiền do code tính.** Quote luôn lấy từ `compute_compensation` trên order row và policy hiện hành. Số ngày trễ hay mã clause viết trong ticket không bao giờ được đưa vào phép tính.
2. **Chỉ host được ghi.** Shape gọi `durability.issue_refund(conn, claim_id, <quote đầy đủ>, crash_at=...)`. Host lo approval, trần theo đơn, idempotency và audit. Shape không tự trừ phần đã hoàn và không bắt `InjectedCrash`.
3. **Trace là ranh giới bảo mật.** Trace chỉ ghi view đã qua allowlist.

Phân công (nhóm 2 người, chia đều theo shape và theo ranh giới an toàn):

| Thành viên | Code | Kiểm chứng | Báo cáo |
| --- | --- | --- | --- |
| Nguyễn Hoàng | `workflow.py`, `single.py` | Crash/idempotency: crash suite 20/20, `tests/test_team_shapes.py` | `group_report.md` |
| Nguyễn Phú Nam | `orchestrator.py` + handoff | Trace/bảo mật: `tests/test_team_security.py`; benchmark 4 shape × 5 seed | `decision_adr.md`, `research_card.md` (R2 + ablation) |

Thứ tự làm: workflow trước (làm baseline và chốt luồng trạng thái), sau đó single và orchestrator dùng lại đúng luồng trạng thái đó, chỉ khác ở phần ai chọn bước đọc tiếp theo.

## 3. Giải pháp

| Shape | Đọc gì | Ai quyết định bước tiếp | Gọi host |
| --- | --- | --- | --- |
| A `workflow` | `get_claim_view` → `lookup_order` → `compute_compensation` | Code, thứ tự cố định | Code gọi `issue_refund` với quote đầy đủ |
| B `single` | Như A, thêm `lookup_refund_history` | MockLLM chọn tool đọc trong `run_react` (tối đa 8 bước, `worker=True` nên tool ghi bị `dispatch` từ chối) | Sau vòng lặp, code đọc lại quote từ **kết quả tool**, không dùng `final` của model, rồi gọi `issue_refund` |
| C `orchestrator` | Orchestrator đọc claim view; investigator chạy `lookup_order`, `lookup_refund_history`, `lookup_policy`, `compute_compensation` | Orchestrator lập kế hoạch rồi giao việc qua handoff | Chỉ orchestrator gọi `issue_refund` |

Luồng trạng thái chung: claim không tồn tại → `failed`; thiếu `order_id` → `needs_info`; đơn không thấy hoặc khác principal → `escalated`; quote = 0 → `denied` và không gọi host; host từ chối → `denied` với `proposal_amount` = quote (host ghi `policy_denied`); conflict → `failed`; thành công → `resolved`. Mọi nhánh trả kết quả qua `common.finish()`, nên trace luôn được ghi kể cả ở các nhánh return sớm.

**Handoff (C):** dựng bằng `make_handoff` với `facts={}` và chỉ tool đọc. Allowlist trong `handoff.py` bỏ mọi key lạ, và hàm sẽ ném lỗi nếu còn sót `CANARY_SECRET_`/`parent_secret`/`raw_headers`. Trace ghi handoff đã sanitize, không ghi parent context.

**Trace:** các event `step`/`observe`/`think`, `quote`, `handoff`, `investigator`, `host`, `crash`, `decision`. Không ghi ticket text, claim row thô hay order row thô.

## 4. Kết quả

Bộ public, 14 claim × seed 11, 22, 33, 44, 55, cùng bảng giá mô phỏng (`src/reports/benchmark.json`):

| Shape | Pass rate | pass^5 | Seed min–max | Variance | Cost/success (VND) | Mean / p95 steps | Model calls TB |
| --- | --: | --: | --: | --: | --: | --: | --: |
| workflow | 1.000 | 1.000 | 1.000–1.000 | 0.000000 | 28.87 | 4.43 / 5 | 1.00 |
| single | 1.000 | 1.000 | 1.000–1.000 | 0.000000 | 40.02 | 10.93 / 12 | 5.64 |
| orchestrator | 1.000 | 1.000 | 1.000–1.000 | 0.000000 | 58.07 | 5.36 / 6 | 2.93 |
| swarm | 0.986 | 0.929 | 0.929–1.000 | 0.000816 | 49.57 | 2.80 / 3 | 3.00 |

- Crash safety: **20/20** (`src/reports/crash.json`). Test của nhóm chạy thêm 3 điểm crash (`before_effect`, `after_effect_before_checkpoint`, `after_checkpoint`) × 3 shape. Sau resume, mỗi trường hợp vẫn đúng 1 dòng ledger và 1 audit `refund_committed`.
- Test student: 248/248 pass (`pytest -m student`). Cổng host: 54/54 pass. Test nhóm: `tests/test_team_shapes.py` 13/13 và `tests/test_team_security.py` 43/43 pass.
- Swarm fail duy nhất ở `R-swarm-C-002-s55`: ticket khai trễ 5 ngày, order row ghi 2 ngày, swarm tin ticket nên refund 20.000 thay vì từ chối. Phân tích ở `research_card.md` (R2).
- Chưa có `student_drop/` nên nhóm chưa tự kiểm trên bộ hidden.

Quyết định kiến trúc: **workflow**, lý do xem `report/team/decision_adr.md`. Phiếu nghiên cứu và ablation: xem `report/team/research_card.md`.

## 5. Khó khăn và cách xử lý

- **Pytest báo `PermissionError` ở `AppData\Local\Temp\pytest-of-<user>`** trên Windows: thư mục temp mặc định bị chặn quyền nên toàn bộ test dùng `tmp_path` đều báo error. Cách xử lý: chạy `python -m pytest -q --basetemp=<thư mục ghi được>`.
- **Quote đầy đủ hay quote đã trừ (T13, T14):** lúc đầu nhóm định trừ phần đã hoàn theo `lookup_refund_history`. Đọc lại contract thì thấy host đã tự trừ, nếu shape trừ thêm thì T14 chỉ ghi 90.000 thay vì 120.000. Nhóm giữ `lookup_refund_history` ở B/C làm dữ kiện để đọc, nhưng không đưa vào phép tính tiền.
- **Single: không tin `final` của model.** `run_react` trả `final` do `decide` tạo. Nhóm chỉ dùng nó để biết vòng lặp đã dừng; status và số tiền do code xác định lại từ kết quả tool.

## 6. Tổng hợp đóng góp

- **Nguyễn Hoàng (2A202603447):** shape workflow và single, crash suite và idempotency, báo cáo nhóm. Báo cáo: `report/team/2A202603447_NguyenHoang.md`.
- **Nguyễn Phú Nam (2A202603501):** shape orchestrator và handoff, kiểm trace/bảo mật, benchmark và ablation R2, ADR và research card. Báo cáo: `report/team/2A202603501_NguyenPhuNam.md`.

Bảng đóng góp (commit và test) nằm trong `TEAM.md`.

## 7. Hạn chế và hướng cải thiện

- MockLLM không phải model sản xuất; latency là `unavailable`; chi phí là chi phí mô phỏng.
- Corpus public chỉ có 14 claim. Pass rate 1.000 của ba shape không có nghĩa là bộ hidden cũng đạt 1.000. Bộ hidden có thể có loại claim mới, ví dụ ticket trích clause cũ hoặc approval trỏ sang claim khác. Logic của nhóm vẫn để host và `compute_compensation` quyết các trường hợp này, nên nhóm kỳ vọng không phải sửa code.
- Kết luận chọn workflow sẽ đảo lại nếu claim cần trích dữ kiện phi cấu trúc mà code không làm được (xem ADR).

## 8. Tài liệu tham khảo

- Cemri et al., *Why Do Multi-Agent LLM Systems Fail?*, NeurIPS 2025 (MAST).
- `docs/business_rules.md`, `docs/contracts.md`, `docs/metrics.md`, `docs/architecture.md` trong repo lab.
