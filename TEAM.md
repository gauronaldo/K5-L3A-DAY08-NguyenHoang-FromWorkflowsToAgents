# Team

## Thông tin nhóm

- Tên nhóm: NguyenHoang
- Lớp: L3A
- Repo nhóm: `K5-L3A-DAY08-NguyenHoang-FromWorkflowsToAgents` (xem [SUBMISSION.md](SUBMISSION.md))
- URL repo, nhánh nộp, commit chốt: https://github.com/gauronaldo/K5-L3A-DAY08-NguyenHoang-FromWorkflowsToAgents · nhánh `main` · commit chốt ghi trong `report/team/decision_adr.md`

## Thành viên

| STT | Họ tên | MSSV | Email | GitHub | Vai trò |
| --: | ------ | ---- | ----- | ------ | ------- |
|   1 | Nguyễn Hoàng | 2A202603447 | hoangng1304@gmail.com | gauronaldo | Shape workflow + single, ledger/crash, báo cáo nhóm |
|   2 | Nguyễn Phú Nam | 2A202603501 | phunam402@gmail.com | Manny402 | Shape orchestrator + handoff, trace/bảo mật, benchmark, ADR + research card |

Gợi ý chia vai:

- Nhóm 6 người: integration; workflow; single agent; orchestrator; ledger/policy/crash; eval/report.
- Nhóm 4 người: workflow + integration; single; orchestrator + handoff; ledger + evaluation.

## Bảng đóng góp

`python -m lab8.check_submission` đọc bảng này bằng máy: giữ nguyên tiêu đề `## Bảng đóng góp` và các cột. Mỗi người một dòng: commit có nội dung và ít nhất một test đã thêm hoặc sửa.

| Người | Vai | Commit | Test đã thêm hoặc sửa |
| --- | --- | --- | --- |
| Nguyễn Hoàng | workflow, single, crash/idempotency, báo cáo nhóm | `feat: shape workflow + single, crash tests, group report (Nguyen Hoang)` | `src/tests/test_team_shapes.py` (13 test: crash 3 điểm × 3 shape rồi resume, claim không tồn tại, step cap của single) |
| Nguyễn Phú Nam | orchestrator + handoff, trace/bảo mật, benchmark, ADR, research card | `feat: shape orchestrator + handoff, security tests, benchmark, ADR, research card (Nguyen Phu Nam)` | `src/tests/test_team_security.py` (43 test: trace/RunResult không lộ secret hay ticket trên 14 claim × 3 shape, worker không gọi được write tool, handoff không cấp được write tool) |

## Cá nhân

Mỗi thành viên đồng thời tạo một báo cáo riêng trong `report/` theo dạng:

```text
report/team/MSSV_HoTen.md
```

Ví dụ: `report/team/20241234_NguyenVanAn.md`.

Sao chép mục dưới đây cho từng thành viên.

## 2A202603447_NguyenHoang

Xem [report/team/2A202603447_NguyenHoang.md](report/team/2A202603447_NguyenHoang.md).

## 2A202603501_NguyenPhuNam

Xem [report/team/2A202603501_NguyenPhuNam.md](report/team/2A202603501_NguyenPhuNam.md).

## MSSV_HoTen (mẫu)

### Phần việc phụ trách

-

### Đóng góp cụ thể

-

### Bằng chứng

-
