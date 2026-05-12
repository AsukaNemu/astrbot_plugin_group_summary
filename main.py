# defaultdict：字典里访问不存在的 key 时，可以自动创建默认值。
# deque：双端队列，这里用它做“固定长度消息缓存”，超过 maxlen 会自动挤掉最旧消息。
from collections import defaultdict, deque

# datetime 用来给缓存的群聊消息打一个当前时间标签。
from datetime import datetime

# AstrBot 提供的日志对象，报错时写日志，方便在控制台/日志文件里排查。
from astrbot.api import logger

# filter：AstrBot 的事件过滤/命令装饰器工具。
# AstrMessageEvent：一条消息事件的类型标注，能让编辑器提示 event 上有哪些方法/字段。
from astrbot.api.event import filter, AstrMessageEvent

# Context：AstrBot 运行上下文，可以拿到当前使用的 LLM provider 等能力。
# Star：AstrBot 插件基类，插件类继承它后才会被 AstrBot 正常加载。
from astrbot.api.star import Context, Star


# 多行字符串，作为发送给大模型的“系统提示词/任务说明”。
# 三个引号 """...""" 可以保留换行，适合写较长的 prompt。
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
不要总结“哈哈哈”“草”“6”“？”这类无意义消息。
如果大量人在围绕某个梗互动，可以简单说“后面主要是在围绕 xxx 玩梗”。

回复要像群友说话，不要像 AI 报告。
不要说“根据聊天记录”“以下是总结”“综上所述”。
可以说：
“省流：……”
“刚刚主要是在聊……”
“结论差不多是……”
“还没定的是……”

如果信息不足，就说“不太够总结，只能看出……”
不要编造没有出现的信息。
"""


# 插件主体类。
# 继承 Star 表示这是一个 AstrBot 插件，AstrBot 会实例化这个类并调用里面被装饰器标记的方法。
class GroupSummaryPlugin(Star):
    def __init__(self, context: Context):
        """
        构造函数：插件被加载时执行一次。

        参数里的 context 是 AstrBot 传进来的运行上下文，后面调用大模型会用到。
        """
        # 调用父类 Star 的初始化逻辑，这是继承类常见写法。
        super().__init__(context)

        # getattr(obj, "name", default) 表示尝试读取 obj.name；
        # 如果属性不存在，就返回 default。
        # `or {}` 是兜底：如果 config 是 None / 空值，就用空字典。
        config = getattr(self, "config", {}) or {}

        # 从配置里读取最多缓存多少条消息。get("key", 默认值) 是字典取值的常用写法。
        # int(...) 确保最终是整数，避免配置里读出来是字符串。
        self.max_messages = int(config.get("max_messages", 50))

        # 是否忽略低信息量短消息，例如“哈哈哈”“6”“？”。
        # bool(...) 把配置值转成布尔值。
        self.ignore_short_message = bool(config.get("ignore_short_message", True))

        # 触发词配置用英文逗号分隔。
        # 如果配置里没有 trigger_words，就使用后面的默认字符串。
        trigger_words_raw = config.get(
            "trigger_words",
            "总结,省流,刚刚聊啥,刚才聊啥,前面聊啥"
        )

        # 列表推导式：
        # - split(",") 把字符串按逗号切成列表
        # - strip() 去掉每个词前后的空白
        # - if word.strip() 过滤掉空字符串
        self.trigger_words = [
            word.strip()
            for word in trigger_words_raw.split(",")
            if word.strip()
        ]

        # key: session_id / group_id
        # value: deque[dict]
        # defaultdict(lambda: deque(...)) 的意思是：
        # 当访问 self.group_buffers[某个新群] 时，自动创建一个新的 deque 缓存。
        # maxlen=self.max_messages 会限制队列最大长度，超过后自动删除最旧的一条。
        self.group_buffers = defaultdict(
            lambda: deque(maxlen=self.max_messages)
        )

    def get_session_key(self, event: AstrMessageEvent) -> str:
        """
        尽量拿到群聊唯一标识。
        不同平台适配器字段可能不完全一致，所以这里写得保守一点。
        """
        # try/except 用来做兼容：某些平台可能没有这个字段或方法。
        # 哪种方式能拿到 session key，就直接 return；失败就继续尝试下一种。
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

        # 所有方式都失败时，给一个兜底 key。
        # 这样插件不会崩，但不同未知会话可能会混在一起，所以只是最后保险。
        return "unknown_session"

    def should_ignore_message(self, text: str) -> bool:
        """
        判断一条消息是否不值得进入缓存。

        返回 True 表示忽略，False 表示应该缓存。
        """
        # strip() 去掉首尾空白，避免“  哈哈  ”这种影响判断。
        text = text.strip()

        # 空消息没有总结价值，直接忽略。
        if not text:
            return True

        # 不把触发词本身塞进缓存，避免污染总结
        # any(...)：只要生成器里有一个条件为 True，整体就为 True。
        # `word in text` 表示判断触发词是否出现在当前消息里。
        if any(word in text for word in self.trigger_words):
            return True

        # 如果配置关闭了“忽略短消息”，上面的空消息/触发词判断之后就都保留。
        if not self.ignore_short_message:
            return False

        # set 集合适合做“某个值是否存在”的判断，速度快，写法也清楚。
        low_info_messages = {
            "哈", "哈哈", "哈哈哈", "草", "6", "？", "?", "。", "啊", "嗯",
            "来了", "在吗", "okk", "ok", "hh", "hhh", "hhhh"
        }

        # 如果消息完全等于这些低信息量文本，就不缓存。
        if text in low_info_messages:
            return True

        # 其他消息默认认为有价值，可以缓存。
        return False

    def is_summary_trigger(self, text: str) -> bool:
        """
        判断当前消息是否包含总结触发词。
        """
        text = text.strip()
        return any(word in text for word in self.trigger_words)

    def cache_message(self, event: AstrMessageEvent):
        """
        把一条群消息缓存进对应群聊的消息队列里。
        """
        # event.message_str 是 AstrBot 提供的纯文本消息内容。
        # `or ""` 是防御式写法：如果 message_str 是 None，就当成空字符串处理。
        text = (event.message_str or "").strip()

        # 低信息量消息、空消息、触发词消息不进入缓存。
        if self.should_ignore_message(text):
            return

        session_key = self.get_session_key(event)

        # 尽量拿发送者昵称；如果平台不支持或报错，就用“某群友”兜底。
        try:
            sender = event.get_sender_name()
        except Exception:
            sender = "某群友"

        # append 往 deque 末尾添加一条消息。
        # 这里每条消息用 dict 存储：时间、发送者、正文。
        self.group_buffers[session_key].append({
            "time": datetime.now().strftime("%H:%M"),
            "sender": sender,
            "text": text
        })

    def build_chat_log(self, session_key: str) -> str:
        """
        把某个群的缓存消息拼成一段文本，供大模型阅读。
        """
        # deque 转 list，方便遍历；这里不修改原缓存。
        messages = list(self.group_buffers[session_key])

        lines = []
        for item in messages:
            # f-string 格式化字符串：
            # 方括号里的 item['time'] 等会被替换成字典里的实际值。
            lines.append(
                f"[{item['time']}] {item['sender']}：{item['text']}"
            )

        # 用换行符把多行聊天记录拼成一个字符串。
        return "\n".join(lines)

    async def call_llm_summary(self, chat_log: str) -> str:
        """
        这里是最容易因 AstrBot 版本不同而需要改的地方。

        思路：
        - 用 AstrBot 当前配置的 provider / LLM
        - 传入 SUMMARY_PROMPT + 群聊记录
        - 拿到纯文本输出

        如果你当前版本没有 self.context.get_using_provider()，
        就去看你本地 AstrBot 的 AI 插件示例，把这里换成对应调用。
        """

        # 把固定总结要求和实际聊天记录组合成完整 prompt。
        prompt = f"""{SUMMARY_PROMPT}

群聊记录：

{chat_log}

请直接输出总结，不要解释你的分析过程。
"""

        # 从 AstrBot 上下文中获取当前正在使用的大模型 provider。
        provider = self.context.get_using_provider()

        # await 表示等待一个异步调用完成。
        # text_chat 是真正向大模型发送 prompt 的地方。
        response = await provider.text_chat(prompt=prompt)

        # 不同 provider 返回值可能不同，做几种兼容
        # 有些实现直接返回字符串。
        if isinstance(response, str):
            return response.strip()

        # 有些实现返回对象，并把文本放在 completion_text 属性里。
        if hasattr(response, "completion_text"):
            return response.completion_text.strip()

        # 有些实现返回对象，并把文本放在 text 属性里。
        if hasattr(response, "text"):
            return response.text.strip()

        # 最后兜底：把返回值强制转成字符串。
        return str(response).strip()

    @filter.command("总结")
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def summarize_command(self, event: AstrMessageEvent):
        """
        `/总结` 命令入口。

        上面的装饰器含义：
        - @filter.command("总结")：只有命令是“总结”时才触发
        - @filter.event_message_type(...)：只处理群聊消息

        async def 表示这是异步函数；AstrBot 会在事件循环里调用它。
        """
        session_key = self.get_session_key(event)
        chat_log = self.build_chat_log(session_key)

        # 如果当前群还没有缓存到有效消息，就直接回复提示，不调用模型。
        if not chat_log.strip():
            # yield event.plain_result(...) 是 AstrBot 插件常见返回方式：
            # yield 把一条回复结果交还给框架发送出去。
            yield event.plain_result("不太够总结，前面没攒到什么有效消息。")
            return

        try:
            summary = await self.call_llm_summary(chat_log)
        except Exception as e:
            # 调模型失败时记录错误，并给群里一个友好的失败提示。
            logger.error(f"群聊总结失败：{e}")
            yield event.plain_result("总结的时候出错了，可能是模型接口没调通。")
            return

        # 成功拿到总结后，把总结文本作为普通消息发回群里。
        yield event.plain_result(summary)

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_group_message(self, event: AstrMessageEvent):
        """
        监听群聊消息：
        - 普通消息：缓存
        - 触发词：总结
        """
        # 每条群消息都会进入这个函数。
        text = (event.message_str or "").strip()
        session_key = self.get_session_key(event)

        # 如果消息里包含触发词，例如“省流”或“刚刚聊啥”，就开始总结。
        if self.is_summary_trigger(text):
            chat_log = self.build_chat_log(session_key)

            if not chat_log.strip():
                yield event.plain_result("不太够总结，前面没攒到什么有效消息。")
                return

            try:
                summary = await self.call_llm_summary(chat_log)
            except Exception as e:
                logger.error(f"群聊总结失败：{e}")
                yield event.plain_result("总结的时候出错了，可能是模型接口没调通。")
                return

            yield event.plain_result(summary)
            return

        # 如果不是触发词消息，就把它当作普通聊天内容缓存起来。
        self.cache_message(event)

    async def terminate(self):
        """
        插件卸载/关闭时调用。

        清空缓存，避免插件停止后还占着内存。
        """
        self.group_buffers.clear()
