from astrbot.api import logger

SUMMARY_PROMPT = """
你是 QQ 群聊总结助手。

用户会给你一段群聊记录，你需要判断大家刚刚在聊什么，并用自然、简短的方式总结。

你要提取：
1. 主要话题
2. 重点信息
3. 有没有结论
4. 有没有待办
5. 有没有争论或玩梗

不要逐句复述。
不要总结"哈哈哈""草""6""？"这类无意义消息。
如果大量人在围绕某个梗互动，可以简单说"后面主要是在围绕 xxx 玩梗"。

回复要像群友说话，不要像 AI 报告。
不要说"根据聊天记录""以下是总结""综上所述"。
可以说：
"省流：……"
"刚刚主要是在聊……"
"结论差不多是……"
"还没定的是……"

如果信息不足，就说"不太够总结，只能看出……"
不要编造没有出现的信息。
"""

PERSONA_PROMPT = """
你是一个群聊总结机器人，你需要把下面这段总结用你的人设重新表达。

你的人设：
{persona}

要求：
- 保留总结的所有关键信息，不要丢掉任何要点
- 用你的人设口吻重新组织语言
- 不要加多余的寒暄或自我介绍，直接输出改写后的总结
- 不要解释你是怎么改写的

原始总结：
{summary}

请直接输出改写后的总结：
"""


class SummaryEngine:
    def __init__(self, context, persona_name: str = ""):
        self.context = context
        self.persona_name = persona_name

    def _get_persona_text(self) -> str:
        if not self.persona_name:
            return ""
        try:
            db = self.context.get_db()
            row = db.execute(
                "SELECT prompt FROM persona WHERE persona_name = ?",
                (self.persona_name,)
            ).fetchone()
            if row and row[0]:
                return row[0]
        except Exception as e:
            logger.warning(f"读取人格设定失败：{e}")
        return ""

    def _extract_response_text(self, response) -> str:
        if isinstance(response, str):
            return response.strip()
        if hasattr(response, "completion_text"):
            return response.completion_text.strip()
        if hasattr(response, "text"):
            return response.text.strip()
        return str(response).strip()

    async def _apply_persona(self, summary: str, persona_text: str) -> str:
        prompt = PERSONA_PROMPT.format(persona=persona_text, summary=summary)
        try:
            provider = self.context.get_using_provider()
            response = await provider.text_chat(prompt=prompt)
            return self._extract_response_text(response)
        except Exception as e:
            logger.warning(f"人格改写失败，返回原始总结：{e}")
            return summary

    async def summarize(self, chat_log: str) -> str:
        prompt = f"""{SUMMARY_PROMPT}

群聊记录：

{chat_log}

请直接输出总结，不要解释你的分析过程。
"""
        provider = self.context.get_using_provider()
        response = await provider.text_chat(prompt=prompt)
        summary = self._extract_response_text(response)

        persona_text = self._get_persona_text()
        if persona_text:
            summary = await self._apply_persona(summary, persona_text)

        return summary
