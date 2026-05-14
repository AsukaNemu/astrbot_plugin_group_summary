from collections import defaultdict, deque
from datetime import datetime


class MessageBuffer:
    def __init__(self, max_messages: int = 50, trigger_words: list = None,
                 ignore_short_message: bool = True):
        self.max_messages = max_messages
        self.ignore_short_message = ignore_short_message
        self.trigger_words = trigger_words or []
        self.group_buffers = defaultdict(
            lambda: deque(maxlen=self.max_messages)
        )

    def should_ignore_message(self, text: str) -> bool:
        text = text.strip()
        if not text:
            return True
        if any(word in text for word in self.trigger_words):
            return True
        if not self.ignore_short_message:
            return False
        low_info_messages = {
            "哈", "哈哈", "哈哈哈", "草", "6", "？", "?", "。", "啊", "嗯",
            "来了", "在吗", "okk", "ok", "hh", "hhh", "hhhh"
        }
        if text in low_info_messages:
            return True
        return False

    def is_summary_trigger(self, text: str) -> bool:
        text = text.strip()
        return any(word in text for word in self.trigger_words)

    def cache_message(self, session_key: str, sender: str, text: str):
        text = text.strip()
        if self.should_ignore_message(text):
            return
        self.group_buffers[session_key].append({
            "time": datetime.now().strftime("%H:%M"),
            "sender": sender,
            "text": text
        })

    def build_chat_log(self, session_key: str) -> str:
        messages = list(self.group_buffers[session_key])
        lines = [
            f"[{item['time']}] {item['sender']}：{item['text']}"
            for item in messages
        ]
        return "\n".join(lines)

    def clear(self):
        self.group_buffers.clear()
