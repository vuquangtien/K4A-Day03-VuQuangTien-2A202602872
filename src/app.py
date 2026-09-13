"""CLI application for the Chatbot vs ReAct Agent lab."""

import argparse
from datetime import datetime, timezone
import json
import os
import sys
import time
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from mcp_server import MCPAcademicServer
from prompts import (
    CHATBOT_BASELINE_PROMPT,
    REACT_AGENT_SYSTEM_PROMPT,
    MAX_ITERATIONS
)
from providers import get_llm_provider

load_dotenv()

def load_test_cases():
    """Load test cases from config/test_cases.json, falling back to the example file."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    if not os.path.exists(config_path):
        example_path = os.path.join(base_dir, "config", "test_cases.example.json")
        if os.path.exists(example_path):
            print("⚠️ [CONFIG NOTICE]: Chưa thấy file 'config/test_cases.json'. Đang dùng mẫu 'config/test_cases.example.json'.")
            print("👉 Hãy chạy: copy config/test_cases.example.json config/test_cases.json và viết test cases theo đề tài của bạn!\n")
            config_path = example_path
        else:
            config_path = "test_cases.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_waterfall_trace(trace_data: list | dict):
    """Write the Waterfall Trace Log to docs/trace_waterfall.json."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    trace_path = os.path.join(docs_dir, "trace_waterfall.json")
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, ensure_ascii=False, indent=2)
    event_count = len(trace_data.get("events", trace_data)) if isinstance(trace_data, dict) else len(trace_data)
    print(f"📊 [OBSERVABILITY]: Đã lưu {event_count} sự kiện Waterfall Trace tại '{trace_path}'!")


def run_baseline_chatbot(user_query: str, provider):
    """Run the baseline chatbot without tools."""
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot phản hồi:\n{response}")


def build_trace_payload(events: list, provider) -> dict:
    """Attach run metadata without storing secrets."""
    provider_name = getattr(provider, "provider_name", provider.__class__.__name__)
    return {
        "run_metadata": {
            "provider": provider_name,
            "model": getattr(provider, "model_name", "unknown"),
            "mode": "offline_mock" if provider_name == "mock" else "live",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "events": events,
    }


def make_tool_result_message(tool_name: str, tool_call_id: str, observation: dict) -> dict:
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "name": tool_name,
        "content": json.dumps(observation, ensure_ascii=False),
    }


def make_synthetic_assistant_message(tool_name: str, arguments: dict, tool_call_id: str) -> dict:
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": tool_call_id,
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(arguments, ensure_ascii=False),
                },
            }
        ],
    }


def run_react_agent(user_query: str, provider, mcp_server: MCPAcademicServer) -> list:
    """Run the ReAct loop and return trace events for this query."""
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")
    
    trace_logs = []
    tools_list = mcp_server.list_tools()
    messages = [{"role": "user", "content": user_query}]
    
    for step in range(1, MAX_ITERATIONS + 1):
        step_start_time = time.perf_counter()
        print(f"\n--- 🔄 Vòng lặp ReAct Loop (Step {step}/{MAX_ITERATIONS}) ---")
        
        llm_response = provider.generate_with_tools(messages, tools_list, system_prompt=REACT_AGENT_SYSTEM_PROMPT)
        llm_latency_ms = round((time.perf_counter() - step_start_time) * 1000, 2)
        
        decision_summary = llm_response.get("decision_summary", "Model returned a decision for this step.")
        print(f"🧠 [Decision]: {decision_summary}")
        
        if llm_response.get("type") == "text":
            final_content = llm_response.get("content", "")
            print(f"🏁 [Final Answer]: {final_content}")
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "decision_summary": decision_summary,
                "answer": final_content,
                "latency_ms": llm_latency_ms
            })
            break
            
        elif llm_response.get("type") == "tool_call":
            tool_name = llm_response.get("tool_name")
            arguments = llm_response.get("arguments", {})
            
            print(f"🛠️ [Action Proposed]: {tool_name}({arguments})")
            
            tool_start_time = time.perf_counter()
            mcp_result = mcp_server.call_tool(tool_name, arguments)
            obs_data = mcp_result.get("result", {})
            tool_latency_ms = round((time.perf_counter() - tool_start_time) * 1000, 2)
            
            obs_str = json.dumps(obs_data, ensure_ascii=False)
            print(f"👁️ [Observation từ MCP Server]: {obs_str}")
            
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "TOOL_EXECUTION",
                "decision_summary": decision_summary,
                "tool_name": tool_name,
                "arguments": arguments,
                "observation": obs_data,
                "latency_ms": round(llm_latency_ms + tool_latency_ms, 2),
                "llm_latency_ms": llm_latency_ms,
                "tool_latency_ms": tool_latency_ms
            })

            tool_call_id = llm_response.get("tool_call_id") or f"local-tool-call-{step}"
            messages.append(
                llm_response.get("assistant_message")
                or make_synthetic_assistant_message(tool_name, arguments, tool_call_id)
            )
            messages.append(make_tool_result_message(tool_name, tool_call_id, obs_data))
            continue

        else:
            raise RuntimeError(f"Provider returned unknown response type: {llm_response}")

    else:
        final_content = f"Agent chưa thể hoàn tất sau {MAX_ITERATIONS} bước ReAct."
        print(f"🏁 [Final Answer]: {final_content}")
        trace_logs.append({
            "step": MAX_ITERATIONS + 1,
            "query": user_query,
            "action_type": "FINAL_ANSWER",
            "decision_summary": "Maximum ReAct steps reached before a final answer.",
            "answer": final_content
        })

    return trace_logs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Day 03 ReAct Agent lab.")
    parser.add_argument("--all", action="store_true", help="Run all configured test cases.")
    parser.add_argument("--interactive", action="store_true", help="Chat with the ReAct Agent.")
    parser.add_argument(
        "--provider",
        choices=["mock", "openai", "gemini"],
        help="Override LLM_PROVIDER from .env. Use mock only for offline development.",
    )
    args = parser.parse_args()

    print("==========================================================")
    print("🏫 VINUNI AI COURSE - DAY 03 LAB: CHATBOT VS REACT AGENT")
    print("==========================================================")
    
    provider = get_llm_provider(args.provider)
    mcp_server = MCPAcademicServer()
    
    print(f"🔌 LLM Provider: {provider.__class__.__name__}")
    print(f"🌐 MCP Server: {mcp_server.server_name}\n")
    
    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases thử nghiệm.\n")
    
    if args.interactive:
        print("🎮 [INTERACTIVE MODE] Trò chuyện trực tiếp với ReAct Agent:")
        print("💡 Gợi ý câu hỏi thử nghiệm:")
        print("   - Câu hỏi chung: 'Quy chế học vụ VinUni yêu cầu bao nhiêu tín chỉ?'")
        print("   - Tra cứu học vụ: 'Hãy tra cứu thông tin học vụ của sinh viên SV2026001'")
        print("   - Đặt lịch hẹn: 'Đặt lịch hẹn tư vấn cho SV2026001 vào 14:00 ngày 15/09/2026'")
        print("   - Gõ 'exit' hoặc 'quit' để kết thúc phiên trò chuyện.\n")
        while True:
            try:
                user_input = input("👤 Sinh viên hỏi: ").strip()
                if not user_input or user_input.lower() in ["exit", "quit"]:
                    print("👋 Tạm biệt! Kết thúc phiên trò chuyện.")
                    break
                logs = run_react_agent(user_input, provider, mcp_server)
                save_waterfall_trace(build_trace_payload(logs, provider))
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Đã thoát phiên tương tác.")
                break
    elif args.all:
        print("🚀 [TEST SUITE MODE] Kiểm tra 5 Test Cases:")
        completed_count = 0
        pending_count = 0
        all_traces = []
        
        for tc in tests:
            print(f"\n==================================================")
            print(f"🧪 [{tc['id']}] Loại test: {tc['type']} (Độ phức tạp: {tc['complexity']})")
            print(f"📌 Kỳ vọng: {tc['expected_behavior']}")
            
            if tc["question"].strip().startswith("PENDING"):
                print(f"⏸️ [CHƯA KÍCH HOẠT]:")
                print(f"   {tc['question']}")
                print(f"   👉 Hãy mở file 'config/test_cases.json' để viết câu hỏi thực tế cho Test Case này!")
                pending_count += 1
            else:
                logs = run_react_agent(tc["question"], provider, mcp_server)
                all_traces.extend(logs)
                completed_count += 1
                
        print(f"\n==================================================")
        print(f"📊 [KẾT QUẢ TEST SUITE]: Đã thực thi {completed_count}/{len(tests)} Test Cases | {pending_count} Test Cases chưa kích hoạt")
        if all_traces:
            save_waterfall_trace(build_trace_payload(all_traces, provider))
        print(f"💡 Để trò chuyện trực tiếp từng câu: Chạy 'python src/app.py --interactive'")
    else:
        # Chế độ mặc định khi chỉ gõ 'python src/app.py'
        print("ℹ️ HƯỚNG DẪN SỬ DỤNG CHƯƠNG TRÌNH:")
        print("  1. Chat trực tiếp liên tục:   python src/app.py --interactive")
        print("  2. Chạy toàn bộ Test Cases:    python src/app.py --all\n")
        
        sample_query = tests[1]["question"]
        print(f"--- 🏁 DEMO CHẠY THỬ 1 TEST CASE MẪU (TC02: Tra cứu học vụ) ---")
        logs = run_react_agent(sample_query, provider, mcp_server)
        save_waterfall_trace(build_trace_payload(logs, provider))
        print("\n💡 Hãy thử ngay lệnh: python src/app.py --interactive để chat trực tiếp!")
