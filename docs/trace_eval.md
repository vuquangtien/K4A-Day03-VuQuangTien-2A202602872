# Báo cáo nghiệm thu Lab 03

**Họ và tên:** Vu Quang Tien
**MSSV:** 2A202602872
**Chủ đề:** Trợ lý Học vụ VinUni

## 1. Agentic Fit Scoring Matrix

| Tiêu chí | Điểm | Giải thích |
| :--- | :---: | :--- |
| Multi-step Reasoning | 4 / 5 | Một số yêu cầu cần tra cứu hồ sơ sinh viên, lấy cố vấn học tập rồi mới đặt lịch. |
| Tool Interaction | 5 / 5 | Agent phải dùng tool để lấy dữ liệu học vụ và thực hiện hành động đặt lịch. |
| Dynamic Decision | 4 / 5 | Agent cần quyết định trả lời trực tiếp, tra cứu, đặt lịch, hoặc xử lý NOT_FOUND tùy query và Observation. |
| Long Horizon Goal | 3 / 5 | Phiên xử lý có thể gồm vài bước liên tiếp, nhưng chưa cần memory dài hạn. |
| **Tổng điểm** | **16 / 20** | Bài toán phù hợp ReAct Agent vì có multi-step flow và tool use rõ ràng. |

## 2. Waterfall Trace Log

Lần nghiệm thu cuối chạy bằng OpenAI live provider:

```json
{
  "provider": "openai",
  "model": "gpt-4o-mini",
  "mode": "live",
  "generated_at": "2026-09-13T16:21:53.054629+00:00"
}
```

Đoạn trace tiêu biểu cho TC04:

```json
[
  {
    "step": 1,
    "query": "Trước tiên hãy tra cứu thông tin học vụ của sinh viên SV2026002, sau đó đặt lịch hẹn tư vấn với đúng cố vấn học tập của sinh viên này vào 09:30 ngày 16/09/2026.",
    "action_type": "TOOL_EXECUTION",
    "decision_summary": "OpenAI selected tool academic_query for the next action.",
    "tool_name": "academic_query",
    "arguments": {
      "student_id": "SV2026002"
    },
    "observation": {
      "status": "SUCCESS",
      "student_id": "SV2026002",
      "data": {
        "full_name": "Trần Thị Bình",
        "class": "AI-K4",
        "gpa": 3.6,
        "email": "binh.tt@vinuni.edu.vn",
        "status": "Đang học",
        "advisor": "TS. Lê Thị B"
      }
    },
    "latency_ms": 1847.93,
    "llm_latency_ms": 1847.83,
    "tool_latency_ms": 0.1
  },
  {
    "step": 2,
    "query": "Trước tiên hãy tra cứu thông tin học vụ của sinh viên SV2026002, sau đó đặt lịch hẹn tư vấn với đúng cố vấn học tập của sinh viên này vào 09:30 ngày 16/09/2026.",
    "action_type": "TOOL_EXECUTION",
    "decision_summary": "OpenAI selected tool schedule_appointment for the next action.",
    "tool_name": "schedule_appointment",
    "arguments": {
      "student_id": "SV2026002",
      "datetime_str": "09:30 16/09/2026",
      "advisor_name": "TS. Lê Thị B"
    },
    "observation": {
      "status": "SUCCESS",
      "booking_id": "BK-SV2026002-99",
      "student_id": "SV2026002",
      "datetime": "09:30 16/09/2026",
      "advisor": "TS. Lê Thị B",
      "message": "Đặt lịch thành công cho sinh viên SV2026002 với TS. Lê Thị B vào lúc 09:30 16/09/2026."
    },
    "latency_ms": 1310.7,
    "llm_latency_ms": 1310.63,
    "tool_latency_ms": 0.07
  },
  {
    "step": 3,
    "query": "Trước tiên hãy tra cứu thông tin học vụ của sinh viên SV2026002, sau đó đặt lịch hẹn tư vấn với đúng cố vấn học tập của sinh viên này vào 09:30 ngày 16/09/2026.",
    "action_type": "FINAL_ANSWER",
    "decision_summary": "OpenAI returned a direct final answer.",
    "answer": "Đã đặt lịch hẹn tư vấn thành công cho sinh viên Trần Thị Bình (SV2026002) với TS. Lê Thị B vào lúc 09:30 ngày 16/09/2026.",
    "latency_ms": 1284.25
  }
]
```

## 3. Kết quả nghiệm thu

- [x] Đã chạy nghiệm thu bằng LLM API thật: OpenAI.
- [x] 5 / 5 testcase đã chạy thành công.
- [x] TC04 thể hiện ReAct multi-step thật: `academic_query` -> Observation -> `schedule_appointment` -> Final Answer.
- [x] Trace log cuối nằm tại `docs/trace_waterfall.json`.
- [ ] Đã Commit và Push mã nguồn thành công lên GitHub cá nhân.

Không có API key hoặc secret trong artifact nộp bài.
