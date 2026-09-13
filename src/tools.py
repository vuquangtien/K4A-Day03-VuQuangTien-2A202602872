"""Tool schemas and execution backend for the academic MCP server."""

import json
from typing import Dict, Any

TOOLS_SCHEMA = [
    {
        "name": "academic_query",
        "description": "Tra cứu hồ sơ và thông tin học vụ của sinh viên VinUni bằng mã sinh viên.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "Mã sinh viên cần tra cứu (ví dụ: 'SV2026001')"
                }
            },
            "required": ["student_id"]
        }
    },
    {
        "name": "schedule_appointment",
        "description": "Đặt lịch hẹn tư vấn học vụ với Cố vấn học tập VinUni.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "Mã sinh viên cần đặt lịch hẹn tư vấn (ví dụ: 'SV2026001')"
                },
                "datetime_str": {
                    "type": "string",
                    "description": "Thời gian hẹn tư vấn theo định dạng dễ đọc (ví dụ: '14:00 15/09/2026')"
                },
                "advisor_name": {
                    "type": "string",
                    "description": "Tên cố vấn học tập sẽ tham gia buổi tư vấn"
                }
            },
            "required": ["student_id", "datetime_str", "advisor_name"]
        }
    }
]

MOCK_DATABASE = {
    "SV2026001": {
        "full_name": "Nguyễn Văn An",
        "class": "AI-K4",
        "gpa": 3.85,
        "email": "an.nv@vinuni.edu.vn",
        "status": "Đang học",
        "advisor": "PGS.TS Nguyễn Văn A"
    },
    "SV2026002": {
        "full_name": "Trần Thị Bình",
        "class": "AI-K4",
        "gpa": 3.60,
        "email": "binh.tt@vinuni.edu.vn",
        "status": "Đang học",
        "advisor": "TS. Lê Thị B"
    }
}


def execute_academic_query(student_id: str) -> str:
    """Look up one student by ID."""
    normalized_id = student_id.strip().upper()
    student = MOCK_DATABASE.get(normalized_id)
    if student:
        return json.dumps({
            "status": "SUCCESS",
            "student_id": normalized_id,
            "data": student
        }, ensure_ascii=False)
    else:
        return json.dumps({
            "status": "NOT_FOUND",
            "student_id": normalized_id,
            "message": f"Không tìm thấy dữ liệu sinh viên có mã '{normalized_id}'"
        }, ensure_ascii=False)


def execute_schedule_appointment(student_id: str, datetime_str: str, advisor_name: str) -> str:
    """Schedule an advising appointment when all required data is valid."""
    normalized_id = student_id.strip().upper()
    advisor = advisor_name.strip()
    appointment_time = datetime_str.strip()
    student = MOCK_DATABASE.get(normalized_id)
    if not student:
        return json.dumps({
            "status": "NOT_FOUND",
            "student_id": normalized_id,
            "message": f"Không thể đặt lịch vì không tìm thấy sinh viên có mã '{normalized_id}'."
        }, ensure_ascii=False)
    if not appointment_time or not advisor:
        return json.dumps({
            "status": "INVALID_ARGUMENT",
            "message": "Thiếu thời gian hẹn hoặc tên cố vấn học tập."
        }, ensure_ascii=False)
    if advisor != student.get("advisor"):
        return json.dumps({
            "status": "ADVISOR_MISMATCH",
            "student_id": normalized_id,
            "expected_advisor": student.get("advisor"),
            "provided_advisor": advisor,
            "message": "Tên cố vấn không khớp với hồ sơ sinh viên."
        }, ensure_ascii=False)
    return json.dumps({
        "status": "SUCCESS",
        "booking_id": f"BK-{normalized_id}-99",
        "student_id": normalized_id,
        "datetime": appointment_time,
        "advisor": advisor,
        "message": f"Đặt lịch thành công cho sinh viên {normalized_id} với {advisor} vào lúc {appointment_time}."
    }, ensure_ascii=False)


TOOL_ROUTER = {
    "academic_query": execute_academic_query,
    "schedule_appointment": execute_schedule_appointment
}


def _tool_schema(tool_name: str) -> Dict[str, Any] | None:
    return next((tool for tool in TOOLS_SCHEMA if tool.get("name") == tool_name), None)


def dispatch_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Validate arguments and execute a registered tool."""
    if tool_name not in TOOL_ROUTER:
        return json.dumps({"status": "UNKNOWN_TOOL", "error": f"Tool '{tool_name}' không tồn tại."}, ensure_ascii=False)

    schema = _tool_schema(tool_name) or {}
    required_fields = schema.get("parameters", {}).get("required", [])
    missing = [field for field in required_fields if not arguments.get(field)]
    if missing:
        return json.dumps({
            "status": "INVALID_ARGUMENT",
            "tool_name": tool_name,
            "missing": missing,
            "message": f"Thiếu tham số bắt buộc: {', '.join(missing)}."
        }, ensure_ascii=False)

    try:
        return TOOL_ROUTER[tool_name](**arguments)
    except TypeError as e:
        return json.dumps({"status": "INVALID_ARGUMENT", "tool_name": tool_name, "error": str(e)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "EXECUTION_ERROR", "tool_name": tool_name, "error": str(e)}, ensure_ascii=False)
