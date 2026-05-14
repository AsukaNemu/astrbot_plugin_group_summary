import sys
import types
from unittest.mock import MagicMock
from collections import deque

# Mock astrbot.api
astrbot = types.ModuleType("astrbot")
astrbot.api = types.ModuleType("astrbot.api")
astrbot.api.logger = MagicMock()
astrbot.api.event = types.ModuleType("astrbot.api.event")
astrbot.api.event.filter = MagicMock()
astrbot.api.event.filter.command = lambda *a, **kw: lambda f: f
astrbot.api.event.filter.event_message_type = lambda *a, **kw: lambda f: f
astrbot.api.event.AstrMessageEvent = MagicMock
astrbot.api.event.filter.EventMessageType = MagicMock(GROUP_MESSAGE=1)
astrbot.api.star = types.ModuleType("astrbot.api.star")
astrbot.api.star.Context = MagicMock
astrbot.api.star.Star = type("Star", (), {"__init__": lambda self, ctx: None})
sys.modules["astrbot"] = astrbot
sys.modules["astrbot.api"] = astrbot.api
sys.modules["astrbot.api.event"] = astrbot.api.event
sys.modules["astrbot.api.star"] = astrbot.api.star

from buffer import MessageBuffer
from summary import SummaryEngine


# --- MessageBuffer 测试 ---

def test_should_ignore_message():
    buf = MessageBuffer(trigger_words=["总结", "省流", "刚刚聊啥"])
    assert buf.should_ignore_message("") is True
    assert buf.should_ignore_message("  ") is True
    assert buf.should_ignore_message("总结") is True
    assert buf.should_ignore_message("帮我总结一下") is True
    assert buf.should_ignore_message("哈") is True
    assert buf.should_ignore_message("6") is True
    assert buf.should_ignore_message("？") is True
    assert buf.should_ignore_message("今天天气不错") is False
    print("[PASS] should_ignore_message")


def test_should_ignore_message_disabled():
    buf = MessageBuffer(ignore_short_message=False, trigger_words=["总结"])
    assert buf.should_ignore_message("哈") is False
    assert buf.should_ignore_message("6") is False
    assert buf.should_ignore_message("") is True
    assert buf.should_ignore_message("总结") is True
    print("[PASS] should_ignore_message (disabled)")


def test_is_summary_trigger():
    buf = MessageBuffer(trigger_words=["总结", "省流", "刚刚聊啥"])
    assert buf.is_summary_trigger("总结") is True
    assert buf.is_summary_trigger("帮我总结一下") is True
    assert buf.is_summary_trigger("省流") is True
    assert buf.is_summary_trigger("刚刚聊啥") is True
    assert buf.is_summary_trigger("你好") is False
    print("[PASS] is_summary_trigger")


def test_cache_and_build():
    buf = MessageBuffer(trigger_words=["总结"])
    buf.cache_message("g1", "Alice", "大家好")
    buf.cache_message("g1", "Bob", "你好")
    buf.cache_message("g1", "Bot", "总结")  # 触发词，应被忽略

    log = buf.build_chat_log("g1")
    assert "[10:00]" not in log or "Alice：大家好" in log
    assert "Bob：你好" in log
    assert "总结" not in log.split("\n")[-1] if log else True
    print("[PASS] cache_and_build")


def test_build_empty():
    buf = MessageBuffer(trigger_words=[])
    assert buf.build_chat_log("empty") == ""
    print("[PASS] build_chat_log (empty)")


def test_clear():
    buf = MessageBuffer(trigger_words=[])
    buf.cache_message("g1", "A", "hello")
    buf.clear()
    assert buf.build_chat_log("g1") == ""
    print("[PASS] clear")


def test_max_messages():
    buf = MessageBuffer(max_messages=3, trigger_words=[])
    for i in range(5):
        buf.cache_message("g1", "U", f"msg{i}")
    log = buf.build_chat_log("g1")
    assert "msg0" not in log
    assert "msg1" not in log
    assert "msg4" in log
    print("[PASS] max_messages")


# --- SummaryEngine 测试 ---

def test_extract_response_text():
    ctx = MagicMock()
    engine = SummaryEngine(ctx)

    assert engine._extract_response_text("hello") == "hello"
    assert engine._extract_response_text("  hello  ") == "hello"

    obj = MagicMock()
    obj.completion_text = "  result  "
    assert engine._extract_response_text(obj) == "result"

    obj2 = MagicMock(spec=[])
    obj2.text = "  another  "
    assert engine._extract_response_text(obj2) == "another"
    print("[PASS] _extract_response_text")


def test_trigger_words_custom():
    buf = MessageBuffer(trigger_words=["自定义词1", "自定义词2"])
    assert buf.is_summary_trigger("自定义词1") is True
    assert buf.is_summary_trigger("自定义词2") is True
    assert buf.is_summary_trigger("总结") is False
    print("[PASS] custom trigger_words")


if __name__ == "__main__":
    test_should_ignore_message()
    test_should_ignore_message_disabled()
    test_is_summary_trigger()
    test_cache_and_build()
    test_build_empty()
    test_clear()
    test_max_messages()
    test_extract_response_text()
    test_trigger_words_custom()
    print("\n全部通过")
