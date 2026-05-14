import sys
import types
from unittest.mock import MagicMock, AsyncMock, patch
from collections import deque

# Mock astrbot.api 模块，避免 import 报错
astrbot = types.ModuleType("astrbot")
astrbot.api = types.ModuleType("astrbot.api")
astrbot.api.logger = MagicMock()
astrbot.api.event = types.ModuleType("astrbot.api.event")
astrbot.api.event.filter = MagicMock()
astrbot.api.event.filter.command = lambda *a, **kw: lambda f: f
astrbot.api.event.filter.event_message_type = lambda *a, **kw: lambda f: f
astrbot.api.event.AstrMessageEvent = MagicMock
astrbot.api.star = types.ModuleType("astrbot.api.star")
astrbot.api.star.Context = MagicMock
astrbot.api.star.Star = type("Star", (), {"__init__": lambda self, ctx: None})
sys.modules["astrbot"] = astrbot
sys.modules["astrbot.api"] = astrbot.api
sys.modules["astrbot.api.event"] = astrbot.api.event
astrbot.api.event.filter.EventMessageType = MagicMock(GROUP_MESSAGE=1)
astrbot.api.star = astrbot.api.star
sys.modules["astrbot.api.star"] = astrbot.api.star

from main import GroupSummaryPlugin


def make_plugin(**config):
    ctx = MagicMock()
    ctx.get_using_provider.return_value = MagicMock()
    plugin = GroupSummaryPlugin(ctx)
    plugin.config = config
    plugin.max_messages = int(config.get("max_messages", 50))
    plugin.ignore_short_message = bool(config.get("ignore_short_message", True))
    plugin.persona = config.get("persona", "").strip()
    trigger_words_raw = config.get("trigger_words", "总结,省流,刚刚聊啥")
    plugin.trigger_words = [w.strip() for w in trigger_words_raw.split(",") if w.strip()]
    from collections import defaultdict
    plugin.group_buffers = defaultdict(lambda: deque(maxlen=plugin.max_messages))
    plugin.version = plugin._load_version()
    return plugin


def test_should_ignore_message():
    p = make_plugin()
    assert p.should_ignore_message("") is True
    assert p.should_ignore_message("  ") is True
    assert p.should_ignore_message("总结") is True
    assert p.should_ignore_message("帮我总结一下") is True
    assert p.should_ignore_message("哈") is True
    assert p.should_ignore_message("6") is True
    assert p.should_ignore_message("？") is True
    assert p.should_ignore_message("今天天气不错") is False
    assert p.should_ignore_message("这个游戏好玩吗") is False
    print("[PASS] should_ignore_message")


def test_should_ignore_message_disabled():
    p = make_plugin(ignore_short_message=False)
    assert p.should_ignore_message("哈") is False
    assert p.should_ignore_message("6") is False
    assert p.should_ignore_message("") is True
    assert p.should_ignore_message("总结") is True
    print("[PASS] should_ignore_message (disabled)")


def test_is_summary_trigger():
    p = make_plugin()
    assert p.is_summary_trigger("总结") is True
    assert p.is_summary_trigger("帮我总结一下") is True
    assert p.is_summary_trigger("省流") is True
    assert p.is_summary_trigger("刚刚聊啥") is True
    assert p.is_summary_trigger("你好") is False
    assert p.is_summary_trigger("今天吃什么") is False
    print("[PASS] is_summary_trigger")


def test_build_chat_log():
    p = make_plugin()
    key = "test_group"
    p.group_buffers[key] = deque([
        {"time": "10:00", "sender": "Alice", "text": "大家好"},
        {"time": "10:01", "sender": "Bob", "text": "你好"},
    ])
    log = p.build_chat_log(key)
    assert "[10:00] Alice：大家好" in log
    assert "[10:01] Bob：你好" in log
    print("[PASS] build_chat_log")


def test_build_chat_log_empty():
    p = make_plugin()
    assert p.build_chat_log("empty_group") == ""
    print("[PASS] build_chat_log (empty)")


def test_load_version():
    p = make_plugin()
    assert p.version.startswith("v")
    assert p.version != "unknown"
    print(f"[PASS] _load_version -> {p.version}")


def test_extract_response_text():
    p = make_plugin()
    assert p._extract_response_text("hello") == "hello"
    assert p._extract_response_text("  hello  ") == "hello"

    obj = MagicMock()
    obj.completion_text = "  result text  "
    assert p._extract_response_text(obj) == "result text"

    obj2 = MagicMock(spec=[])
    obj2.text = "  another text  "
    assert p._extract_response_text(obj2) == "another text"
    print("[PASS] _extract_response_text")


def test_trigger_words_config():
    p = make_plugin(trigger_words="自定义词1,自定义词2")
    assert p.is_summary_trigger("自定义词1") is True
    assert p.is_summary_trigger("自定义词2") is True
    assert p.is_summary_trigger("总结") is False
    print("[PASS] trigger_words config")


if __name__ == "__main__":
    test_should_ignore_message()
    test_should_ignore_message_disabled()
    test_is_summary_trigger()
    test_build_chat_log()
    test_build_chat_log_empty()
    test_load_version()
    test_extract_response_text()
    test_trigger_words_config()
    print("\n全部通过")
