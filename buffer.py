from collections import defaultdict, deque
from datetime import datetime


class MessageBuffer:
    def __init__(self, max_messages: int = 50, trigger_words: list = None,
                 ignore_short_message: bool = True,
                 summary_engine = None,
                 ai_intent_detection: bool = True):
        self.max_messages = max_messages
        self.ignore_short_message = ignore_short_message
        self.trigger_words = trigger_words or []
        self.summary_engine = summary_engine
        self.ai_intent_detection = ai_intent_detection
        self.group_buffers = defaultdict(
            lambda: deque(maxlen=self.max_messages)
        )

    async def should_ignore_message(self, text: str) -> bool:
        text = text.strip()
        if not text:
            return True
        # 如果是总结触发消息，忽略缓存
        if await self.is_summary_trigger(text):
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

    async def is_summary_trigger(self, text: str) -> bool:
        text = text.strip().lower()
        if not text:
            return False

        # 第一级：精确匹配触发词（优先级最高，快速返回）
        if any(word in text for word in self.trigger_words):
            return True

        # 第二级：规则模糊匹配
        # 检查是否是单人指代（问特定某个人的，不是问全体）
        # 注意："你们"是复数，不算单人
        has_single_person_prefix = False
        if text.startswith("你") and not text.startswith("你们"):
            has_single_person_prefix = True
        elif text.startswith("他") and not text.startswith("他们"):
            has_single_person_prefix = True
        elif text.startswith("她") and not text.startswith("她们"):
            has_single_person_prefix = True
        elif text.startswith("它") and not text.startswith("它们"):
            has_single_person_prefix = True

        # 其他排除前缀（指代特定事物、询问原因或特定两个人的）
        other_exclude_prefixes = [
            "这", "那", "这个", "那个", "这些", "那些",
            "咋", "为啥", "为什么", "咋的", "搞啥", "干哈",
            "你俩", "你们俩", "他俩", "他们俩", "她俩", "她们俩"
        ]
        has_other_exclude_prefix = any(text.startswith(p) for p in other_exclude_prefixes)

        # 语义模糊匹配：识别询问聊天内容的意图
        intent_patterns = [
            # 询问聊天内容的模式
            ["聊", "什么"], ["聊", "啥"], ["说", "什么"], ["说", "啥"],
            ["讲", "什么"], ["讲", "啥"], ["说啥呢"], ["聊啥呢"],
            ["说什么了"], ["聊什么了"], ["刚才说啥"], ["刚刚说啥"],
            ["前面", "内容"], ["刚才", "内容"], ["回顾", "一下"],
            ["总结", "一下"], ["省流", "一下"],

            # 表达看不懂/不明白的模式
            ["看不懂"], ["看不明白"], ["什么", "意思"], ["啥", "意思"],
            ["啥情况"], ["怎么回事"],
        ]

        # 询问全体聊天的关键词（即使有复数前缀也触发）
        group_chat_keywords = {"聊", "刚才", "前面", "回顾", "总结", "省流"}

        rule_result = False
        for pattern in intent_patterns:
            if all(keyword in text for keyword in pattern):
                # 如果是询问全体聊天的内容，不管前缀（除了单人指代）都触发
                if any(k in group_chat_keywords for k in pattern):
                    # 只有当是单人前缀（问特定某个人）时才不触发
                    if not has_single_person_prefix:
                        rule_result = True
                        break
                # 其他模式（看不懂、啥意思、啥情况等）
                else:
                    # 不能有任何排除前缀
                    if not has_single_person_prefix and not has_other_exclude_prefix:
                        rule_result = True
                        break

        # 规则匹配到直接返回
        if rule_result:
            return True

        # 第三级：AI意图识别（只有规则没匹配到，且开启了AI识别时才调用）
        if not self.ai_intent_detection or not self.summary_engine:
            return False

        try:
            # 构建意图判断Prompt，要求LLM只回答是或否
            prompt = f"""请判断用户说的这句话是不是想要总结之前的群聊内容。
如果用户是在询问刚才大家聊了什么、看不懂聊天内容、想要省流总结等，回答"是"。
如果用户是在调侃、询问特定的人、询问特定事物、或者其他和总结群聊无关的内容，回答"否"。
只需要回答"是"或"否"，不要其他任何内容。
用户的话：{text}"""

            # 调用LLM
            response = await self.summary_engine.context.llm(prompt)
            result = self.summary_engine._extract_response_text(response).strip().lower()

            # 判断结果
            return "是" in result or "yes" in result

        except Exception as e:
            # AI调用失败时降级到规则判断
            return False

    async def cache_message(self, session_key: str, sender: str, text: str):
        text = text.strip()
        if await self.should_ignore_message(text):
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
