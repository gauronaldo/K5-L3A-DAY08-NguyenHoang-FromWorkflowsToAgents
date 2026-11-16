# Research card

File này nằm cố định ở `report/team/research_card.md`; `python -m lab8.check_submission` đọc cột "Nhóm điền" bằng máy.

Phần này nối tiếp phần mini research ở buổi lý thuyết (slide 62–63). Chọn **một** câu R1–R4, điền 6 dòng, rồi biến nó thành **một ablation** chạy được trong lab: giữ nguyên model (MockLLM), tool, seed, corpus và giá, chỉ thay đổi một biến.

| Câu | Nguồn (thư viện tham khảo, slide 68–69) | Câu hỏi gợi ý cho lab |
| --- | --- | --- |
| R1 · Scaling | Google Research 2026, *Towards a Science of Scaling Agent Systems* | Task claims chủ yếu tuần tự hay song song được? Dự đoán thêm investigator sẽ làm pass rate và cost/success thay đổi thế nào. |
| R2 · Failure taxonomy | MAST, NeurIPS 2025, *Why Do Multi-Agent LLM Systems Fail?* | Các trial fail của swarm (seed 55) thuộc nhóm nào: lỗi giao việc, lệch mục tiêu, hay lỗi kiểm chứng? |
| R3 · Architecture choices | AgentArch, AACL 2026 | Nếu đổi topology mà giữ nguyên mọi thứ khác, biến nào phải cố định để kết luận còn đúng? |
| R4 · Evaluation confounders | EMNLP 2026, *Rethinking Evaluation of MAS Efficiency* | Làm sao chứng minh chênh lệch giữa A/B/C/D là do topology, không phải do prompt, tool hay seed? |

## Phiếu của nhóm

Điền vào cột cuối. Không xóa hai cột đầu.

| Field | Hướng dẫn | Nhóm điền |
| --- | --- | --- |
| CÂU | R1 / R2 / R3 / R4 | R2 |
| SOURCE | Paper/blog, năm, URL, loại bằng chứng (benchmark, production report, blog kinh nghiệm) | Cemri et al., *Why Do Multi-Agent LLM Systems Fail?* (MAST), NeurIPS 2025 Datasets & Benchmarks, arXiv:2503.13657; loại bằng chứng: taxonomy lỗi rút ra từ trace có gán nhãn của nhiều framework MAS |
| CLAIM | Một kết luận gốc của nguồn. Không viết rộng hơn phạm vi paper | Lỗi của hệ multi-agent rơi vào 3 nhóm lớn: lỗi đặc tả/thiết kế hệ thống, lệch hướng giữa các agent (inter-agent misalignment), và lỗi kiểm chứng/kết thúc nhiệm vụ (task verification) |
| BOUNDARY | Model / dataset / setup giới hạn kết luận đó | Taxonomy rút từ trace của các framework MAS dùng LLM thật trên task lập trình và toán; lab dùng MockLLM có điểm yếu cài sẵn, corpus 14 claim public, nên chỉ kiểm được việc phân loại một lỗi cụ thể, không kiểm được tần suất các nhóm lỗi |
| HYPOTHESIS | Nếu đổi shape A→B (hoặc bật/tắt một thành phần), metric X sẽ đổi theo hướng nào, khoảng bao nhiêu | Lỗi của swarm ở C-002 seed 55 thuộc nhóm task verification: không đối chiếu số ngày trễ trong ticket với order row. Bỏ phần peer và phần tin ticket (swarm → orchestrator, giữ nguyên investigator) thì pass rate ở seed 55 tăng từ 0.929 lên 1.000, còn cost/success thay đổi dưới ±15% |
| METHOD | Biến giữ cố định: model, tools, seed, corpus, giá, evaluator. Biến duy nhất được thay đổi: … | Giữ cố định: MockLLM, bộ tool chỉ đọc, run_readonly_investigators, seed 55, corpus data/public_claims.jsonl, pricing.yaml, evaluator lab8.metrics.trial_pass. Biến duy nhất được thay đổi: topology swarm (có peer, tin số trễ trong ticket) → orchestrator (quote chỉ từ order row) |
| FAILURE / METRIC | Một lỗi dự kiến và cách đo nó: pass rate, pass^5, variance, cost/success, leak, bypass | Lỗi dự kiến: refund sai khi ticket khai trễ 5 ngày trong khi DB ghi 2 ngày (status resolved thay vì denied). Đo bằng pass rate và pass^5 trên seed 55, kèm cost/success; thêm số trial approval bypass/leak (kỳ vọng 0) |

## Kết quả ablation

- Lệnh đã chạy (copy nguyên văn): `python -m lab8.benchmark --shapes swarm,orchestrator --cases data/public_claims.jsonl --seeds 55 --out reports/ablation_r2_seed55.json`
- Run id / file report: `src/reports/ablation_r2_seed55.json`; trial fail `R-swarm-C-002-s55`, đối chứng `R-orchestrator-C-002-s55`
- Kết quả so với hypothesis (đúng / sai / không kết luận được), kèm số liệu: **đúng**. Ở seed 55, swarm đạt pass 0.929 (13/14) và fail đúng một trial C-002 với `status resolved != denied`; orchestrator đạt 1.000 (14/14). Cost/success 53.23 → 58.07 VND (+9%, nằm trong ±15%). Trace swarm có event `model_override` ghi lại lúc agent ghi đè số ngày trễ bằng con số trong ticket mà không kiểm chứng với DB, khớp nhóm *task verification* (và một phần *disobey task specification*) của MAST. Host không chặn được lỗi này vì approval của C-002 hợp lệ, chỉ có số tiền là tính sai.
- Giới hạn: MockLLM không phải model sản xuất, latency là `unavailable`.

Muốn đi xa hơn một ablation để lấy điểm cộng thì xem [docs/bonus_topics.md](../../docs/bonus_topics.md).
