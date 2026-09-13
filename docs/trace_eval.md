# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** Vu Quang Tien  
> **Mã Sinh Viên / Mã Học viên:** 2A202602872  
> **Chủ đề Lựa chọn:** Trợ lý Học vụ VinUni

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm |
| :--- | :---: | :--- |
| **1. Multi-step Reasoning** | 4 / 5 | Một số yêu cầu cần tách thành nhiều bước như tra cứu hồ sơ sinh viên, xác định cố vấn học tập rồi mới đặt lịch tư vấn. |
| **2. Tool Interaction** | 5 / 5 | Hệ thống bắt buộc gọi MCP Server để tra cứu dữ liệu học vụ và thực hiện hành động đặt lịch, không thể chỉ trả lời bằng văn bản. |
| **3. Dynamic Decision** | 4 / 5 | Agent phải quyết định trả lời trực tiếp, gọi `academic_query`, gọi `schedule_appointment`, hoặc xử lý trường hợp không tìm thấy sinh viên tùy theo Observation. |
| **4. Long Horizon Goal** | 3 / 5 | Mục tiêu của phiên tư vấn có thể kéo dài qua vài bước trong cùng một yêu cầu, dù chưa cần memory dài hạn như autonomous agent. |
| **TỔNG ĐIỂM AGENTIC FIT** | **16 / 20** | Bài toán phù hợp triển khai Agentic System vì tổng điểm lớn hơn 12/20 và có nhu cầu tool use rõ ràng. |

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE TRÊN API THẬT)

> ⚠️ **YÊU CẦU NGHIỆM THU:** Mở tệp `.env` điền `GEMINI_API_KEY` (hoặc `OPENAI_API_KEY`) để kết nối LLM thật trước khi thực thi `python src/app.py --all`. Bài nộp chỉ dùng Mock Offline Provider sẽ không đạt điểm nghiệm thực tế.

Dán 1 đoạn trích xuất log tiêu biểu từ file `docs/trace_waterfall.json` sinh ra từ phản hồi LLM API thật:

```json
[
  {
    "step": 1,
    "query": "Trước tiên hãy tra cứu thông tin học vụ của sinh viên SV2026002, sau đó đặt lịch hẹn tư vấn với đúng cố vấn học tập của sinh viên này vào 09:30 ngày 16/09/2026.",
    "action_type": "TOOL_EXECUTION",
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
    "latency_ms": 2091.98
  },
  {
    "step": 2,
    "query": "Trước tiên hãy tra cứu thông tin học vụ của sinh viên SV2026002, sau đó đặt lịch hẹn tư vấn với đúng cố vấn học tập của sinh viên này vào 09:30 ngày 16/09/2026.",
    "action_type": "TOOL_EXECUTION",
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
    "latency_ms": 0.07
  }
]
```

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [x] Đã điền API Key thật trong `.env` và xác nhận Agent chạy mượt mà trên LLM API thật (OpenAI).
- **Tổng số Test Cases đã chạy thành công:** 5 / 5 test cases.
- **Số lượt gọi Tool qua MCP Server chính xác:** 5 lượt.
- **Kết quả đẩy Repo nộp bài:** [ ] Đã Commit và Push mã nguồn thành công lên GitHub cá nhân.

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!
