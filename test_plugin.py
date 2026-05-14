import sys
import types
import asyncio
from unittest.mock import MagicMock, AsyncMock
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

async def test_should_ignore_message():
    # 关闭AI识别，测试规则匹配
    buf = MessageBuffer(trigger_words=["总结", "省流", "刚刚聊啥"], ai_intent_detection=False)
    assert await buf.should_ignore_message("") is True
    assert await buf.should_ignore_message("  ") is True
    assert await buf.should_ignore_message("总结") is True
    assert await buf.should_ignore_message("帮我总结一下") is True
    assert await buf.should_ignore_message("哈") is True
    assert await buf.should_ignore_message("6") is True
    assert await buf.should_ignore_message("？") is True
    assert await buf.should_ignore_message("今天天气不错") is False
    print("[PASS] should_ignore_message")


async def test_should_ignore_message_disabled():
    buf = MessageBuffer(ignore_short_message=False, trigger_words=["总结"], ai_intent_detection=False)
    assert await buf.should_ignore_message("哈") is False
    assert await buf.should_ignore_message("6") is False
    assert await buf.should_ignore_message("") is True
    assert await buf.should_ignore_message("总结") is True
    print("[PASS] should_ignore_message (disabled)")


async def test_is_summary_trigger():
    buf = MessageBuffer(trigger_words=["总结", "省流", "刚刚聊啥"], ai_intent_detection=False)
    assert await buf.is_summary_trigger("总结") is True
    assert await buf.is_summary_trigger("帮我总结一下") is True
    assert await buf.is_summary_trigger("省流") is True
    assert await buf.is_summary_trigger("刚刚聊啥") is True
    assert await buf.is_summary_trigger("你好") is False
    print("[PASS] is_summary_trigger")


async def test_cache_and_build():
    buf = MessageBuffer(trigger_words=["总结"], ai_intent_detection=False)
    await buf.cache_message("g1", "Alice", "大家好")
    await buf.cache_message("g1", "Bob", "你好")
    # 触发词，should_ignore会返回True，所以不会被缓存
    assert await buf.should_ignore_message("总结") is True
    await buf.cache_message("g1", "Bot", "总结")

    log = buf.build_chat_log("g1")
    assert "[10:00]" not in log or "Alice：大家好" in log
    assert "Bob：你好" in log
    assert "总结" not in log
    print("[PASS] cache_and_build")


def test_build_empty():
    buf = MessageBuffer(trigger_words=[])
    assert buf.build_chat_log("empty") == ""
    print("[PASS] build_chat_log (empty)")


async def test_clear():
    buf = MessageBuffer(trigger_words=[], ai_intent_detection=False)
    await buf.cache_message("g1", "A", "hello")
    buf.clear()
    assert buf.build_chat_log("g1") == ""
    print("[PASS] clear")


async def test_max_messages():
    buf = MessageBuffer(max_messages=3, trigger_words=[], ai_intent_detection=False)
    for i in range(5):
        await buf.cache_message("g1", "U", f"msg{i}")
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


async def test_trigger_words_custom():
    buf = MessageBuffer(trigger_words=["自定义词1", "自定义词2"], ai_intent_detection=False)
    assert await buf.is_summary_trigger("自定义词1") is True
    assert await buf.is_summary_trigger("自定义词2") is True
    assert await buf.is_summary_trigger("总结") is False
    print("[PASS] custom trigger_words")


async def test_fuzzy_intent_matching():
    buf = MessageBuffer(trigger_words=["总结", "省流"], ai_intent_detection=False)
    # 测试模糊匹配的意图
    assert await buf.is_summary_trigger("聊了什么") is True
    assert await buf.is_summary_trigger("刚才说啥") is True
    assert await buf.is_summary_trigger("看不懂你们说啥") is True
    assert await buf.is_summary_trigger("什么意思啊") is True
    assert await buf.is_summary_trigger("讲了啥啊") is True
    assert await buf.is_summary_trigger("前面内容回顾一下") is True
    assert await buf.is_summary_trigger("啥情况这是") is True
    assert await buf.is_summary_trigger("怎么回事啊") is True
    assert await buf.is_summary_trigger("刚刚说什么了") is True
    # 测试排除规则：指代特定对象的不触发
    assert await buf.is_summary_trigger("你俩啥情况啊") is False  # 调侃，不是总结
    assert await buf.is_summary_trigger("他怎么回事啊") is False  # 指代特定的人
    assert await buf.is_summary_trigger("这啥意思啊") is False     # 指代特定事物
    assert await buf.is_summary_trigger("那个咋回事") is False    # 指代特定事物
    assert await buf.is_summary_trigger("你说啥呢") is False       # 问特定的人
    assert await buf.is_summary_trigger("你们刚才说啥呢") is True # 问大家刚才聊的内容，应该触发
    assert await buf.is_summary_trigger("你们聊啥呢") is True     # 问大家聊的内容，应该触发
    # 测试其他不应该触发的情况
    assert await buf.is_summary_trigger("今天天气真好") is False
    assert await buf.is_summary_trigger("我吃饭去了") is False
    assert await buf.is_summary_trigger("什么东西好吃") is False
    assert await buf.is_summary_trigger("为啥不吃饭") is False
    assert await buf.is_summary_trigger("咋搞的啊") is False
    print("[PASS] fuzzy intent matching")


async def run_all_tests():
    await test_should_ignore_message()
    await test_should_ignore_message_disabled()
    await test_is_summary_trigger()
    await test_cache_and_build()
    test_build_empty()
    await test_clear()
    await test_max_messages()
    test_extract_response_text()
    await test_trigger_words_custom()
    await test_fuzzy_intent_matching()
    print("\n全部通过")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
