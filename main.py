from pathlib import Path

from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star

from summary import SummaryEngine
from buffer import MessageBuffer


class GroupSummaryPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        config = getattr(self, "config", {}) or {}

        trigger_words_raw = config.get(
            "trigger_words", "总结,省流,刚刚聊啥,刚才聊啥,前面聊啥,聊了什么,说啥了,刚才说什么,看不懂,说的啥,什么意思,讲了啥,前面内容,回顾一下,说什么了,聊啥呢,啥情况"
        )
        trigger_words = [
            w.strip() for w in trigger_words_raw.split(",") if w.strip()
        ]

        self.engine = SummaryEngine(
            context=context,
            persona_name=config.get("persona", "").strip(),
        )

        self.buffer = MessageBuffer(
            max_messages=int(config.get("max_messages", 50)),
            trigger_words=trigger_words,
            ignore_short_message=bool(config.get("ignore_short_message", True)),
            summary_engine=self.engine,
            ai_intent_detection=bool(config.get("ai_intent_detection", True)),
        )

        self.version = self._load_version()

    def _load_version(self) -> str:
        try:
            meta_path = Path(__file__).parent / "metadata.yaml"
            for line in meta_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("version:"):
                    return line.split(":", 1)[1].split("#")[0].strip()
        except Exception:
            pass
        return "unknown"

    def _get_session_key(self, event: AstrMessageEvent) -> str:
        try:
            return event.unified_msg_origin
        except Exception:
            pass
        try:
            return event.get_session_id()
        except Exception:
            pass
        try:
            return str(event.message_obj.group_id)
        except Exception:
            pass
        return "unknown_session"

    async def _cache_event_message(self, event: AstrMessageEvent):
        text = (event.message_str or "").strip()
        if await self.buffer.should_ignore_message(text):
            return
        session_key = self._get_session_key(event)
        try:
            sender = event.get_sender_name()
        except Exception:
            sender = "某群友"
        await self.buffer.cache_message(session_key, sender, text)

    async def _do_summary(self, event: AstrMessageEvent):
        session_key = self._get_session_key(event)
        chat_log = self.buffer.build_chat_log(session_key)

        if not chat_log.strip():
            yield event.plain_result("不太够总结，前面没攒到什么有效消息。")
            return

        try:
            summary = await self.engine.summarize(chat_log)
        except Exception as e:
            logger.error(f"群聊总结失败：{e}")
            yield event.plain_result("总结的时候出错了，可能是模型接口没调通。")
            return

        yield event.plain_result(summary)

    @filter.command("总结")
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def summarize_command(self, event: AstrMessageEvent):
        async for r in self._do_summary(event):
            yield r
        # 阻止事件继续传播，避免被其他处理器重复处理
        event.stop_event()

    @filter.command(".version")
    async def version_command(self, event: AstrMessageEvent):
        yield event.plain_result(f"astrbot_plugin_group_summary {self.version}")

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_group_message(self, event: AstrMessageEvent):
        text = (event.message_str or "").strip()

        if await self.buffer.is_summary_trigger(text):
            async for r in self._do_summary(event):
                yield r
            # 阻止事件继续传播，避免被其他处理器（如自带Agent）重复处理
            event.stop_event()
            return

        await self._cache_event_message(event)

    async def terminate(self):
        self.buffer.clear()
