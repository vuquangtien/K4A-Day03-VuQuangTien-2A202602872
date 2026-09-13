"""LLM provider adapters for text generation and native tool calling."""

import json
import os
import re
import sys
from typing import Any, Dict, List, Union
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

MessagesInput = Union[str, List[Dict[str, Any]]]


def normalize_messages(messages: MessagesInput) -> List[Dict[str, Any]]:
    if isinstance(messages, str):
        return [{"role": "user", "content": messages}]
    return [dict(message) for message in messages]


def _extract_student_id(text: str) -> str | None:
    match = re.search(r"SV\d{7}", text, flags=re.IGNORECASE)
    return match.group(0).upper() if match else None


def _extract_datetime(text: str) -> str | None:
    patterns = [
        r"\d{1,2}:\d{2}\s*(?:ngày\s*)?\d{1,2}/\d{1,2}/\d{4}",
        r"\d{1,2}h(?:\d{2})?\s*(?:ngày\s*)?\d{1,2}/\d{1,2}/\d{4}",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = re.sub(r"\s*ngày\s*", " ", match.group(0), flags=re.IGNORECASE).strip()
            return re.sub(r"^(\d{1,2})h\s", r"\1:00 ", value)
    return None


def _extract_named_advisor(text: str) -> str | None:
    match = re.search(r"\bvới\s+(.+?)\s+vào\b", text, flags=re.IGNORECASE)
    if not match:
        return None
    advisor = match.group(1).strip()
    if "cố vấn" in advisor.lower():
        return None
    return advisor


def _booking_intent(text: str) -> bool:
    lowered = text.lower()
    return "đặt lịch" in lowered or "hẹn tư vấn" in lowered


def _lookup_intent(text: str) -> bool:
    lowered = text.lower()
    return "tra cứu" in lowered or "thông tin học vụ" in lowered or "cố vấn" in lowered


def _original_user_query(messages: List[Dict[str, Any]]) -> str:
    for message in messages:
        if message.get("role") == "user":
            return str(message.get("content", ""))
    return ""


def _last_tool_observation(messages: List[Dict[str, Any]]) -> tuple[str | None, Dict[str, Any] | None]:
    for message in reversed(messages):
        if message.get("role") == "tool":
            try:
                return message.get("name"), json.loads(str(message.get("content", "{}")))
            except json.JSONDecodeError:
                return message.get("name"), {"status": "INVALID_OBSERVATION", "raw": message.get("content", "")}
    return None, None


class BaseLLMProvider:
    """Common interface for providers that support text and tool-enabled calls."""
    provider_name = "base"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError

    def generate_with_tools(self, messages: MessagesInput, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        raise NotImplementedError


class MockOfflineProvider(BaseLLMProvider):
    """Deterministic provider for local/offline testing only."""
    provider_name = "mock"

    def __init__(self):
        self.model_name = "Offline-Mock-Model-2026"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return f"[Mock Chatbot Response]: Xin chào! Tôi đã nhận được câu hỏi '{prompt}'. (Chế độ Chatbot không có Tool tra cứu dữ liệu thời gian thực)."

    def generate_with_tools(self, messages: MessagesInput, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        normalized = normalize_messages(messages)
        prompt = _original_user_query(normalized)
        student_id = _extract_student_id(prompt)
        datetime_str = _extract_datetime(prompt)
        advisor_name = _extract_named_advisor(prompt)
        last_tool_name, observation = _last_tool_observation(normalized)

        if observation and last_tool_name == "academic_query":
            if observation.get("status") != "SUCCESS":
                return {
                    "type": "text",
                    "content": observation.get("message", "Không tìm thấy dữ liệu phù hợp."),
                    "decision_summary": "Observation shows the lookup did not return a student record."
                }
            if _booking_intent(prompt):
                data = observation.get("data", {})
                advisor = data.get("advisor")
                if not datetime_str:
                    return {
                        "type": "text",
                        "content": "Bạn vui lòng cung cấp thời gian cụ thể để đặt lịch tư vấn.",
                        "decision_summary": "A booking request still needs an appointment time."
                    }
                if not advisor:
                    return {
                        "type": "text",
                        "content": "Hồ sơ sinh viên không có thông tin cố vấn nên chưa thể đặt lịch.",
                        "decision_summary": "The lookup succeeded but did not include an advisor."
                    }
                return {
                    "type": "tool_call",
                    "tool_name": "schedule_appointment",
                    "arguments": {
                        "student_id": observation.get("student_id"),
                        "datetime_str": datetime_str,
                        "advisor_name": advisor,
                    },
                    "decision_summary": "Observation provides the assigned advisor, so the next action is scheduling."
                }
            data = observation.get("data", {})
            return {
                "type": "text",
                "content": (
                    f"Kết quả tra cứu cho sinh viên {observation.get('student_id')} ({data.get('full_name')}): "
                    f"Lớp {data.get('class')}, GPA: {data.get('gpa')}, Email: {data.get('email')}, "
                    f"Trạng thái: {data.get('status')}, Cố vấn: {data.get('advisor')}."
                ),
                "decision_summary": "Observation contains the requested academic record."
            }

        if observation and last_tool_name == "schedule_appointment":
            return {
                "type": "text",
                "content": observation.get("message", json.dumps(observation, ensure_ascii=False)),
                "decision_summary": "Observation confirms the booking result."
            }

        if _booking_intent(prompt) and not student_id:
            return {
                "type": "text",
                "content": "Bạn vui lòng cung cấp mã sinh viên để mình đặt lịch tư vấn.",
                "decision_summary": "The user wants a booking but has not provided a student ID."
            }

        if student_id and _booking_intent(prompt) and (_lookup_intent(prompt) or not advisor_name):
            return {
                "type": "tool_call",
                "tool_name": "academic_query",
                "arguments": {"student_id": student_id},
                "decision_summary": "The booking needs the student's assigned advisor before scheduling."
            }

        if student_id and _booking_intent(prompt):
            if not datetime_str or not advisor_name:
                return {
                    "type": "text",
                    "content": "Bạn vui lòng cung cấp đủ thời gian hẹn và tên cố vấn để đặt lịch.",
                    "decision_summary": "The booking request is missing required scheduling arguments."
                }
            return {
                "type": "tool_call",
                "tool_name": "schedule_appointment",
                "arguments": {
                    "student_id": student_id,
                    "datetime_str": datetime_str,
                    "advisor_name": advisor_name,
                },
                "decision_summary": "The user provided all required booking fields."
            }

        if student_id or _lookup_intent(prompt):
            if not student_id:
                return {
                    "type": "text",
                    "content": "Bạn vui lòng cung cấp mã sinh viên cần tra cứu.",
                    "decision_summary": "A lookup requires a concrete student ID."
                }
            return {
                "type": "tool_call",
                "tool_name": "academic_query",
                "arguments": {"student_id": student_id},
                "decision_summary": "The user asked for student-specific academic data."
            }

        return {
            "type": "text",
            "content": "Quy chế học vụ cơ bản gồm đăng ký môn học đúng hạn, tham dự lớp theo quy định, hoàn thành đánh giá giữa kỳ/cuối kỳ, tích lũy đủ tín chỉ và tuân thủ quy định thi cử.",
            "decision_summary": "The question is general policy and does not require a tool."
        }


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider."""
    provider_name = "gemini"

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-2.5-flash"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            raise RuntimeError("GEMINI_API_KEY chưa được cấu hình. Dùng --provider mock nếu muốn chạy offline.")
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.models.generate_content(model=self.model_name, contents=contents)
            return response.text
        except Exception as e:
            raise RuntimeError(f"Gemini API error: {e}") from e

    def _messages_to_prompt(self, messages: List[Dict[str, Any]]) -> str:
        lines = []
        for message in messages:
            role = message.get("role", "user")
            if role == "tool":
                lines.append(f"Observation from {message.get('name')}: {message.get('content', '')}")
            else:
                content = message.get("content", "")
                if content:
                    lines.append(f"{role}: {content}")
        return "\n\n".join(lines)

    def generate_with_tools(self, chat_history: MessagesInput, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            raise RuntimeError("GEMINI_API_KEY chưa được cấu hình. Dùng --provider mock nếu muốn chạy offline.")
        
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            normalized = normalize_messages(chat_history)

            function_declarations = []
            for tool in tools_schema:
                if not tool.get("name") or not tool.get("parameters"):
                    continue
                function_declarations.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {})
                })

            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
                tools=[{"function_declarations": function_declarations}] if function_declarations else None,
                temperature=0.2
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=self._messages_to_prompt(normalized),
                config=config
            )

            if response.function_calls:
                call = response.function_calls[0]
                args = dict(call.args) if hasattr(call, 'args') and call.args else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.name,
                    "arguments": args,
                    "decision_summary": f"Gemini selected tool {call.name} for the next action."
                }
            else:
                return {
                    "type": "text",
                    "content": response.text or "",
                    "decision_summary": "Gemini returned a direct final answer."
                }

        except Exception as e:
            raise RuntimeError(f"Gemini API error: {e}") from e


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider using Chat Completions native tool calling."""
    provider_name = "openai"

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            raise RuntimeError("OPENAI_API_KEY chưa được cấu hình. Dùng --provider mock nếu muốn chạy offline.")
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(model=self.model_name, messages=messages)
            return response.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}") from e

    def generate_with_tools(self, chat_history: MessagesInput, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            raise RuntimeError("OPENAI_API_KEY chưa được cấu hình. Dùng --provider mock nếu muốn chạy offline.")

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)

            tools = []
            for tool in tools_schema:
                if not tool.get("name"):
                    continue
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {})
                    }
                })

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.extend(normalize_messages(chat_history))

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                parallel_tool_calls=False,
                temperature=0.2
            )

            msg = response.choices[0].message
            if msg.tool_calls:
                call = msg.tool_calls[0]
                try:
                    args = json.loads(call.function.arguments) if call.function.arguments else {}
                except json.JSONDecodeError as exc:
                    raise RuntimeError(f"OpenAI returned malformed tool arguments for {call.function.name}: {exc}") from exc
                assistant_message = {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.function.name,
                                "arguments": call.function.arguments or "{}",
                            },
                        }
                    ],
                }
                return {
                    "type": "tool_call",
                    "tool_name": call.function.name,
                    "arguments": args,
                    "tool_call_id": call.id,
                    "assistant_message": assistant_message,
                    "decision_summary": f"OpenAI selected tool {call.function.name} for the next action."
                }
            else:
                return {
                    "type": "text",
                    "content": msg.content or "",
                    "decision_summary": "OpenAI returned a direct final answer."
                }
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"OpenAI API error: {e}") from e


def get_llm_provider(provider_override: str | None = None) -> BaseLLMProvider:
    """Create the requested provider. Mock mode must be selected explicitly."""
    provider_type = (provider_override or os.getenv("LLM_PROVIDER", "gemini")).lower()
    
    if provider_type == "gemini":
        return GeminiProvider()
    elif provider_type == "openai":
        return OpenAIProvider()
    elif provider_type == "mock":
        return MockOfflineProvider()
    raise ValueError(f"LLM_PROVIDER không hợp lệ: {provider_type}. Chọn gemini, openai hoặc mock.")
