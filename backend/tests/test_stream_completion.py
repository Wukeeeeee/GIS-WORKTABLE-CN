"""工具执行成功后，流式收尾必须保留产物并发出 done 事件。"""
import json
import time
from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from backend.services import graph, storage_service


def test_tool_stream_returns_results_and_usage(monkeypatch):
    request = HumanMessage(content="从广州到北京画一张专题图")
    call = AIMessage(content="", tool_calls=[{
        "name": "draw_feature", "args": {}, "id": "call-map",
    }])
    tool_result = ToolMessage(
        content="图层与图片已生成", name="draw_feature", tool_call_id="call-map",
    )
    answer = AIMessage(content="已生成专题图。")
    final_messages = [request, call, tool_result, answer]
    pending = {
        "layers": [{"name": "广州到北京"}],
        "images": ["/output/corridor.png"],
        "heatmap": None, "clear_layers": False, "layer_ops": [],
        "aoi_suggestions": None, "qa_warnings": [],
    }

    class FakeAgent:
        def stream(self, *args, **kwargs):
            for end in (2, 3, 4):
                yield {"messages": final_messages[:end]}

    monkeypatch.setattr(graph, "build_llm", lambda cfg: object())
    monkeypatch.setattr(graph, "create_react_agent", lambda *a: FakeAgent())
    monkeypatch.setattr(graph, "_cached_graph", None, raising=False)
    monkeypatch.setattr(graph, "tools", [])
    monkeypatch.setattr(graph, "reset_state", lambda *a: None)
    monkeypatch.setattr(graph, "set_current_task", lambda *a: None)
    monkeypatch.setattr(graph, "get_pending_state", lambda: pending)
    monkeypatch.setattr(graph, "_auto_promote_pending", lambda *a: None)
    monkeypatch.setattr(graph.task_manager, "find_or_create_task", lambda *a: "test-task")
    monkeypatch.setattr(graph.pending_action, "set_active_session", lambda *a: None)
    monkeypatch.setattr(graph.pending_action, "get_pending_action", lambda *a: None)
    monkeypatch.setattr(storage_service, "record_run_start", lambda *a: None)
    finished = []
    monkeypatch.setattr(storage_service, "record_run_finish", lambda *a: finished.append(a))
    guard_calls = []

    def guard(text, state, **kwargs):
        guard_calls.append(kwargs)
        return text, {"ok": True}

    monkeypatch.setattr(graph.result_guard, "apply_guard", guard)
    usage_calls = []

    def usage(**kwargs):
        usage_calls.append(kwargs)
        return {"total_tokens": 42}

    monkeypatch.setattr(graph, "extract_and_record_token_usage", usage)
    started = time.time()
    events = [json.loads(line.removeprefix("data: ")) for line in graph.run_agent_stream(
        messages=[SystemMessage(content="GIS 助手"), request], cfg=SimpleNamespace(model="test-model"),
        original_message=request.content, session_id="test-stream-completion",
    )]

    assert [event["type"] for event in events] == ["tool_start", "tool_end", "thinking", "done"]
    done = events[-1]
    assert done["response"] == answer.content
    assert done["layers"] == pending["layers"]
    assert done["images"] == pending["images"]
    assert done["token_usage"] == {"total_tokens": 42}
    assert started <= guard_calls[0]["run_start_time"] <= time.time()
    assert usage_calls[0]["messages"] == final_messages
    assert usage_calls[0]["duration_ms"] >= 0
    assert finished[0][2:] == ("success", "PASS")
    assert graph._tools_mod.acquire_session_lock("test-stream-completion")
    graph._tools_mod.release_session_lock("test-stream-completion")
