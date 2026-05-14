---
name: astrbot-official-api-reference
description: AstrBot 官方接口与插件开发速查 Skill。用于开发 AstrBot 插件、调用 AstrBot HTTP API、处理消息事件、发送消息、调用 AI、配置插件、存储数据、编写会话控制器与上传 Skills。
---

# AstrBot 官方接口文档 Skill

## 使用边界

当用户询问 AstrBot 插件开发、HTTP API、消息事件、消息链、主动发送、调用 AI、插件配置、插件存储、会话控制、插件 Pages、插件国际化、平台适配器或 Skills 时，优先参考本 Skill。若接口行为与当前 AstrBot 版本不一致，以官方文档和运行中 AstrBot 的 `/scalar.html` 或 WebUI 为准。

官方入口：

- 官方文档主页：`https://docs.astrbot.app/`
- AstrBot GitHub：`https://github.com/AstrBotDevs/AstrBot`
- 插件市场：`https://plugins.astrbot.app/`
- HTTP API 交互式文档：`https://docs.astrbot.app/scalar.html`
- 插件开发起点：`https://docs.astrbot.app/dev/star/plugin-new.html`
- 最小实例：`https://docs.astrbot.app/dev/star/guides/simple.html`
- 接收消息事件：`https://docs.astrbot.app/dev/star/guides/listen-message-event.html`
- 发送消息：`https://docs.astrbot.app/dev/star/guides/send-message.html`
- 插件配置：`https://docs.astrbot.app/dev/star/guides/plugin-config.html`
- 插件 Pages：`https://docs.astrbot.app/dev/star/guides/plugin-pages.html`
- 插件国际化：`https://docs.astrbot.app/dev/star/guides/plugin-i18n.html`
- 调用 AI：`https://docs.astrbot.app/dev/star/guides/ai.html`
- 插件存储：`https://docs.astrbot.app/dev/star/guides/storage.html`
- 会话控制器：`https://docs.astrbot.app/dev/star/guides/session-control.html`
- Anthropic Skills：`https://docs.astrbot.app/use/skills.html`

---

## 1. AstrBot HTTP API

AstrBot 从 v4.18.0 开始提供基于 API Key 的 HTTP API。

### 1.1 鉴权

在 WebUI → 设置中创建 API Key，请求头二选一：

```http
Authorization: Bearer abk_xxx
```

或：

```http
X-API-Key: abk_xxx
```

### 1.2 Scope 权限

| Scope | 作用 | 可访问接口 |
|---|---|---|
| `chat` | 调用对话能力、查询会话 | `POST /api/v1/chat`、`GET /api/v1/chat/sessions` |
| `config` | 获取可用配置文件列表 | `GET /api/v1/configs` |
| `file` | 上传附件文件，获取 `attachment_id` | `POST /api/v1/file` |
| `im` | 主动发送 IM 消息、查询 bot/platform 列表 | `POST /api/v1/im/message`、`GET /api/v1/im/bots` |

### 1.3 常用接口

| 方法 | 路径 | 用途 | 关键参数 |
|---|---|---|---|
| `POST` | `/api/v1/chat` | 调用 AstrBot 内建 Agent 对话，SSE 流式返回 | `username` 必填；`session_id` 可选；`message` 必填 |
| `GET` | `/api/v1/chat/sessions` | 分页获取指定用户会话 | `username` 必填 |
| `GET` | `/api/v1/configs` | 获取可用配置文件列表 | 需要 `config` scope |
| `POST` | `/api/v1/file` | 上传附件并得到 `attachment_id` | multipart 文件上传 |
| `POST` | `/api/v1/im/message` | 按 UMO 主动发消息 | `umo`、`message` |
| `GET` | `/api/v1/im/bots` | 获取 bot/platform ID 列表 | 需要 `im` scope |

### 1.4 `message` 字段格式

`POST /api/v1/chat` 和 `POST /api/v1/im/message` 的 `message` 支持两种形式。

#### 纯文本

```json
{
  "message": "Hello"
}
```

#### 消息段数组 message chain

```json
{
  "message": [
    { "type": "plain", "text": "请看这个文件" },
    { "type": "file", "attachment_id": "9a2f8c72-e7af-4c0e-b352-111111111111" }
  ]
}
```

| type | 必填字段 | 可选字段 | 说明 |
|---|---|---|---|
| `plain` | `text` | - | 文本段 |
| `reply` | `message_id` | `selected_text` | 引用回复。当前主要适配 `/api/v1/chat` |
| `image` | `attachment_id` | - | 图片附件段 |
| `record` | `attachment_id` | - | 音频附件段 |
| `file` | `attachment_id` | - | 通用文件段 |
| `video` | `attachment_id` | - | 视频附件段 |

注意：`attachment_id` 来自 `POST /api/v1/file`。`reply` 不能作为唯一内容，至少需要一个实际内容段。

### 1.5 Chat API 示例

```bash
curl -N 'http://localhost:6185/api/v1/chat' \
  -H 'Authorization: Bearer abk_xxx' \
  -H 'Content-Type: application/json' \
  -d '{"message":"Hello","username":"alice"}'
```

复杂消息：

```json
{
  "username": "alice",
  "session_id": "my_session_001",
  "message": [
    { "type": "plain", "text": "帮我总结这个 PDF" },
    { "type": "file", "attachment_id": "9a2f8c72-e7af-4c0e-b352-111111111111" }
  ],
  "enable_streaming": true
}
```

### 1.6 IM 主动消息示例

```json
{
  "umo": "webchat:FriendMessage:openapi_probe",
  "message": [
    { "type": "plain", "text": "这是主动消息" },
    { "type": "image", "attachment_id": "9a2f8c72-e7af-4c0e-b352-222222222222" }
  ]
}
```

---

## 2. 插件基础结构

### 2.1 插件目录

推荐插件仓库命名：

- 以 `astrbot_plugin_` 开头；
- 不包含空格；
- 全小写；
- 尽量短。

插件目录通常位于：

```text
AstrBot/data/plugins/<plugin_name>/
```

必须维护 `metadata.yaml`，AstrBot 识别插件元数据依赖该文件。

### 2.2 最小插件 `main.py`

```python
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star
from astrbot.api import logger

class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("helloworld")
    async def helloworld(self, event: AstrMessageEvent):
        """这是一个 hello world 指令"""
        user_name = event.get_sender_name()
        message_str = event.message_str
        logger.info("触发 hello world 指令")
        yield event.plain_result(f"Hello, {user_name}!")

    async def terminate(self):
        """插件卸载/停用时调用，可选实现。"""
        pass
```

规则：

- 插件类必须继承 `Star`。
- `Context` 用于插件与 AstrBot Core 交互。
- Handler 必须写在插件类中。
- Handler 的前两个参数必须是 `self` 和 `event`。
- 插件入口文件名应为 `main.py`。

---

## 3. 消息事件接口

### 3.1 导入

```python
from astrbot.api.event import filter, AstrMessageEvent
```

### 3.2 `AstrMessageEvent`

`AstrMessageEvent` 是消息事件对象，包含发送者、消息内容等信息。常用属性/方法：

| 接口 | 说明 |
|---|---|
| `event.message_str` | 纯文本消息内容 |
| `event.message_obj` | 原始 AstrBotMessage 对象 |
| `event.get_sender_name()` | 获取发送者昵称 |
| `event.get_sender_id()` | 获取发送者 ID |
| `event.plain_result(text)` | 构造纯文本回复 |
| `event.image_result(path_or_url)` | 构造图片回复 |
| `event.chain_result(chain)` | 构造消息链回复 |
| `event.make_result()` | 创建可自定义的消息结果 |
| `event.send(result_or_text)` | 主动在当前事件上下文中发送消息，钩子/会话控制中常用 |
| `event.stop_event()` | 阻止事件继续传递 |
| `event.unified_msg_origin` | 当前会话唯一来源字符串，可用于之后主动发消息 |

### 3.3 `AstrBotMessage`

```python
class AstrBotMessage:
    type: MessageType
    self_id: str
    session_id: str
    message_id: str
    group_id: str = ""
    sender: MessageMember
    message: list[BaseMessageComponent]
    message_str: str
    raw_message: object
    timestamp: int
```

说明：

- `message` 是消息链，如 `[Plain("Hello"), At(qq=123456)]`。
- `message_str` 是消息链中 Plain 文本拼接后的纯文本。
- `raw_message` 是平台适配器给出的原始消息对象。

### 3.4 常见消息段

跨平台常见：

- `Plain`：文本
- `At`：提及
- `Image`：图片
- `Record`：语音
- `Video`：视频
- `File`：文件

OneBot v11 常见扩展：

- `Face`：表情
- `Node`：合并转发节点
- `Nodes`：多个合并转发节点
- `Poke`：戳一戳

---

## 4. 指令与过滤器

### 4.1 普通指令

```python
@filter.command("helloworld")
async def helloworld(self, event: AstrMessageEvent):
    yield event.plain_result("Hello!")
```

注意：指令名不要带空格。

### 4.2 带参指令

```python
@filter.command("add")
def add(self, event: AstrMessageEvent, a: int, b: int):
    yield event.plain_result(f"结果是: {a + b}")
```

调用：

```text
/add 1 2
```

### 4.3 指令组

```python
@filter.command_group("math")
def math(self):
    pass

@math.command("add")
async def add(self, event: AstrMessageEvent, a: int, b: int):
    yield event.plain_result(f"结果是: {a + b}")

@math.command("sub")
async def sub(self, event: AstrMessageEvent, a: int, b: int):
    yield event.plain_result(f"结果是: {a - b}")
```

调用：

```text
/math add 1 2
/math sub 1 2
```

嵌套指令组使用 `.group()`：

```python
@math.group("calc")
def calc(self):
    pass
```

### 4.4 指令别名

```python
@filter.command("help", alias={"帮助", "helpme"})
def help(self, event: AstrMessageEvent):
    yield event.plain_result("帮助内容")
```

### 4.5 事件类型过滤

```python
@filter.event_message_type(filter.EventMessageType.ALL)
async def on_all_message(self, event: AstrMessageEvent):
    yield event.plain_result("收到消息")
```

私聊：

```python
@filter.event_message_type(filter.EventMessageType.PRIVATE_MESSAGE)
async def on_private_message(self, event: AstrMessageEvent):
    yield event.plain_result("收到私聊消息")
```

群聊：

```python
@filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
async def on_group_message(self, event: AstrMessageEvent):
    yield event.plain_result("收到群聊消息")
```

### 4.6 平台过滤

```python
@filter.platform_adapter_type(
    filter.PlatformAdapterType.AIOCQHTTP | filter.PlatformAdapterType.QQOFFICIAL
)
async def on_specific_platform(self, event: AstrMessageEvent):
    yield event.plain_result("指定平台消息")
```

常见值：

- `AIOCQHTTP`
- `QQOFFICIAL`
- `GEWECHAT`
- `ALL`

### 4.7 权限过滤

```python
@filter.permission_type(filter.PermissionType.ADMIN)
@filter.command("test")
async def test(self, event: AstrMessageEvent):
    yield event.plain_result("管理员可用")
```

多个过滤器是 AND 逻辑，必须全部通过才会执行。

---

## 5. 事件钩子

钩子通常不与 `@filter.command`、`@filter.command_group`、`@filter.event_message_type`、`@filter.platform_adapter_type`、`@filter.permission_type` 混用。

### 5.1 AstrBot 初始化完成

```python
@filter.on_astrbot_loaded()
async def on_astrbot_loaded(self):
    print("AstrBot 初始化完成")
```

### 5.2 等待 LLM 请求

```python
@filter.on_waiting_llm_request()
async def on_waiting_llm(self, event: AstrMessageEvent):
    await event.send("正在等待请求...")
```

### 5.3 LLM 请求前

```python
from astrbot.api.provider import ProviderRequest
from astrbot.core.agent.message import TextPart

@filter.on_llm_request()
async def on_llm_request(self, event: AstrMessageEvent, req: ProviderRequest):
    req.extra_user_content_parts.append(
        TextPart(text="<runtime_hint>本轮提示</runtime_hint>").mark_as_temp()
    )
```

建议：动态上下文优先放入 `req.extra_user_content_parts`，不要每轮拼接到 `req.system_prompt`，否则容易破坏提示词缓存并增加成本。

### 5.4 LLM 响应后

```python
from astrbot.api.provider import LLMResponse

@filter.on_llm_response()
async def on_llm_resp(self, event: AstrMessageEvent, resp: LLMResponse):
    print(resp)
```

### 5.5 Agent 生命周期

```python
from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.astr_agent_context import AstrAgentContext

@filter.on_agent_begin()
async def on_agent_begin(self, event: AstrMessageEvent, run_context: ContextWrapper[AstrAgentContext]):
    print("Agent 开始运行")
```

```python
@filter.on_agent_done()
async def on_agent_done(self, event: AstrMessageEvent, resp: LLMResponse):
    print("Agent 运行完成")
```

### 5.6 LLM 工具调用前后

```python
from astrbot.core.agent.tool import FunctionTool

@filter.on_using_llm_tool()
async def on_using_llm_tool(self, event: AstrMessageEvent, tool: FunctionTool, tool_args: dict | None):
    print(tool.name, tool_args)
```

```python
from mcp.types import CallToolResult
from astrbot.core.agent.tool import FunctionTool

@filter.on_llm_tool_respond()
async def on_llm_tool_respond(
    self,
    event: AstrMessageEvent,
    tool: FunctionTool,
    tool_args: dict | None,
    tool_result: CallToolResult | None,
):
    print(tool.name, tool_args, tool_result)
```

---

## 6. 发送消息接口

### 6.1 被动回复

```python
@filter.command("helloworld")
async def helloworld(self, event: AstrMessageEvent):
    yield event.plain_result("Hello!")
    yield event.plain_result("你好！")
    yield event.image_result("path/to/image.jpg")
    yield event.image_result("https://example.com/image.jpg")
```

### 6.2 主动消息

保存当前会话 UMO：

```python
umo = event.unified_msg_origin
```

之后用 `Context` 发送：

```python
from astrbot.api.event import MessageChain

message_chain = MessageChain().message("Hello!").file_image("path/to/image.jpg")
await self.context.send_message(umo, message_chain)
```

`unified_msg_origin` 是会话唯一 ID，AstrBot 依靠它找到正确平台和会话。

### 6.3 富媒体消息链

```python
import astrbot.api.message_components as Comp

@filter.command("pic")
async def pic(self, event: AstrMessageEvent):
    chain = [
        Comp.At(qq=event.get_sender_id()),
        Comp.Plain("来看这个图："),
        Comp.Image.fromURL("https://example.com/image.jpg"),
        Comp.Image.fromFileSystem("path/to/image.jpg"),
        Comp.Plain("这是一个图片。")
    ]
    yield event.chain_result(chain)
```

文件：

```python
Comp.File(file="path/to/file.txt", name="file.txt")
```

语音：

```python
Comp.Record(file="path/to/record.wav", url="path/to/record.wav")
```

视频：

```python
from astrbot.api.message_components import Video

Video.fromFileSystem(path="test.mp4")
Video.fromURL(url="https://example.com/video.mp4")
```

---

## 7. 插件配置接口

### 7.1 `_conf_schema.json`

在插件目录添加 `_conf_schema.json`：

```json
{
  "token": {
    "description": "Bot Token",
    "type": "string"
  },
  "sub_config": {
    "description": "嵌套配置",
    "type": "object",
    "items": {
      "name": {
        "description": "名称",
        "type": "string"
      },
      "time": {
        "description": "时间",
        "type": "int",
        "default": 123
      }
    }
  }
}
```

### 7.2 Schema 字段

| 字段 | 说明 |
|---|---|
| `type` | 必填。支持 `string`、`text`、`int`、`float`、`bool`、`object`、`list`、`dict`、`template_list`、`file` |
| `description` | 配置说明 |
| `hint` | 鼠标悬浮提示 |
| `obvious_hint` | 是否醒目显示提示 |
| `default` | 默认值 |
| `items` | object/dict 子 Schema |
| `invisible` | 是否在面板隐藏 |
| `options` | 下拉选项 |
| `editor_mode` | 代码编辑器模式，需较新版本 |
| `editor_language` | 编辑器语言，默认 `json` |
| `editor_theme` | `vs-light` 或 `vs-dark` |
| `_special` | WebUI 特殊选择器 |

### 7.3 `_special` 常用值

| 值 | 用途 | 返回 |
|---|---|---|
| `select_provider` | 选择模型提供商 | 字符串 |
| `select_provider_tts` | 选择 TTS 提供商 | 字符串 |
| `select_provider_stt` | 选择 STT 提供商 | 字符串 |
| `select_persona` | 选择人格 | 字符串 |
| `select_knowledgebase` | 选择知识库 | list，支持多选 |

不要使用官方标注为内部实现的 `_special` 值。

### 7.4 插件中读取配置

```python
from astrbot.api import AstrBotConfig
from astrbot.api.star import Context, Star

class ConfigPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        print(self.config)
        # self.config.save_config()
```

AstrBot 会在载入插件时检测 `_conf_schema.json`，生成并维护 `data/config/<plugin_name>_config.json`。

---

## 8. 插件存储接口

### 8.1 简单 KV 存储

需要 AstrBot >= 4.9.2。

```python
class Main(Star):
    @filter.command("hello")
    async def hello(self, event: AstrMessageEvent):
        await self.put_kv_data("greeted", True)
        greeted = await self.get_kv_data("greeted", False)
        await self.delete_kv_data("greeted")
```

接口：

- `await self.put_kv_data(key, value)`
- `await self.get_kv_data(key, default)`
- `await self.delete_kv_data(key)`

### 8.2 大文件存储目录

大文件建议存放：

```text
data/plugin_data/{plugin_name}/
```

获取路径：

```python
from pathlib import Path
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

plugin_data_path = Path(get_astrbot_data_path()) / "plugin_data" / self.name
```

---

## 9. 会话控制器

适用于需要多轮交互的插件，如成语接龙、问卷、配置向导。

```python
import astrbot.api.message_components as Comp
from astrbot.core.utils.session_waiter import session_waiter, SessionController
from astrbot.api.event import filter, AstrMessageEvent

@filter.command("成语接龙")
async def idiom_game(self, event: AstrMessageEvent):
    yield event.plain_result("请发送一个成语~")

    @session_waiter(timeout=60, record_history_chains=False)
    async def waiter(controller: SessionController, event: AstrMessageEvent):
        idiom = event.message_str

        if idiom == "退出":
            await event.send(event.plain_result("已退出成语接龙~"))
            controller.stop()
            return

        if len(idiom) != 4:
            await event.send(event.plain_result("成语必须是四个字"))
            return

        result = event.make_result()
        result.chain = [Comp.Plain("先见之明")]
        await event.send(result)
        controller.keep(timeout=60, reset_timeout=True)

    try:
        await waiter(event)
    except TimeoutError:
        yield event.plain_result("你超时了！")
    finally:
        event.stop_event()
```

要点：

- 会话控制内部发送消息使用 `await event.send(...)`，不要 `yield`。
- `controller.keep()` 继续等待下一轮输入。
- `controller.stop()` 立即结束会话。
- `controller.get_history_chains()` 可获取历史消息链，前提是记录历史。

---

## 10. 调用 AI / LLM 能力

常见做法：

1. 在普通指令中整理用户输入。
2. 使用 AstrBot 的 provider / agent 能力请求 LLM。
3. 对流式或非流式响应做格式化。
4. 需要动态上下文时，优先在 `on_llm_request` 中通过 `req.extra_user_content_parts` 添加。
5. 需要让模型按需调用能力时，优先注册 `llm_tool`，不要把所有大段资料塞入 prompt。

推荐模式：

```python
@filter.command("总结")
async def summarize(self, event: AstrMessageEvent):
    text = event.message_str
    # 这里调用插件自己的总结逻辑，或接入 AstrBot provider / agent。
    yield event.plain_result("总结结果...")
```

---

## 11. 插件 Pages / WebUI 扩展

用于给插件添加管理页面。适用场景：

- 表情包管理；
- 数据库查看；
- 自定义配置界面；
- 任务队列管理；
- 插件状态面板。

开发时应参考官方 `插件 Pages` 文档，并注意鉴权、路径隔离和静态资源组织。

---

## 12. 插件国际化

适用对象：

- 插件文案；
- 配置项 `description`；
- 配置项 `hint`；
- 下拉选项 labels；
- WebUI 页面文本。

推荐：插件对外展示文本不要硬编码，统一抽离到语言资源文件。

---

## 13. 平台适配器开发

当目标聊天平台官方未支持或社区适配不满足需求时，可开发平台适配器。适配器核心工作：

- 接收平台消息；
- 转换为 AstrBot 标准消息对象；
- 实现消息发送；
- 处理富媒体、回复、群聊、私聊、用户 ID、会话 ID；
- 映射平台特殊能力。

优先参考官方“接入平台适配器”文档。

---

## 14. AstrBot Skills

AstrBot 在 v4.13.0 后支持 Anthropic Skills。

### 14.1 Skill 上传格式

上传 zip，解压后必须是一个 Skill 文件夹：

```text
my_skill/
  SKILL.md
  scripts/
  references/
```

要求：

- zip 解压后的文件夹名是 Skill 标识；
- 文件夹名建议英文；
- 文件夹内必须有 `SKILL.md`；
- `SKILL.md` 建议符合 Anthropic Skills 规范。

### 14.2 执行环境

AstrBot 当前提供：

- `Local`：Agent 在 AstrBot 运行环境执行代码，存在安全风险；
- `Sandbox`：Agent 在隔离沙盒执行，需启动 AstrBot 沙盒模式。

使用 Local 时，AstrBot 目前仅允许管理员请求真正操作本地环境，普通用户会被权限限制。

---

## 15. 开发排错清单

### 插件不加载

检查：

- 插件目录是否在 `AstrBot/data/plugins/`；
- 文件名是否为 `main.py`；
- 插件类是否继承 `Star`；
- `metadata.yaml` 是否存在且正确；
- 依赖是否安装；
- WebUI 插件管理中是否启用；
- 修改后是否重载插件。

### 指令不触发

检查：

- 是否导入 `from astrbot.api.event import filter`；
- Handler 是否写在插件类中；
- Handler 参数是否为 `self, event, ...`；
- 指令名是否包含空格；
- 权限过滤是否阻止普通用户；
- 平台过滤/消息类型过滤是否不匹配；
- 是否被其他插件 `stop_event()` 截断。

### 图片/文件发不出去

检查：

- 平台是否支持该消息段；
- 本地文件路径是否存在；
- URL 是否以 `http://` 或 `https://` 开头；
- 协议端和机器人端是否能访问同一文件路径；
- 视频/语音格式是否符合平台要求。

### HTTP API 返回 403

检查：

- API Key 是否正确；
- 请求头是否正确；
- API Key 是否包含目标接口所需 scope。

### `/api/v1/chat` 报参数错误

检查：

- `username` 是否填写；
- `message` 是否为空；
- `reply` 是否作为唯一消息段；
- 附件是否先通过 `/api/v1/file` 上传并拿到 `attachment_id`。

---

## 16. 推荐插件开发模板

```python
from astrbot.api import logger, AstrBotConfig
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
import astrbot.api.message_components as Comp

class Main(Star):
    def __init__(self, context: Context, config: AstrBotConfig | None = None):
        super().__init__(context)
        self.config = config or {}

    @filter.command("ping", alias={"测试"})
    async def ping(self, event: AstrMessageEvent):
        """测试插件是否运行"""
        logger.info("ping command triggered")
        yield event.plain_result("pong")

    @filter.command("echo")
    async def echo(self, event: AstrMessageEvent, *, text: str = ""):
        """复读文本"""
        if not text:
            yield event.plain_result("请输入要复读的内容")
            return
        yield event.plain_result(text)

    @filter.command("rich")
    async def rich(self, event: AstrMessageEvent):
        """发送消息链"""
        chain = [
            Comp.At(qq=event.get_sender_id()),
            Comp.Plain(" 这是消息链示例")
        ]
        yield event.chain_result(chain)

    async def terminate(self):
        logger.info("plugin terminated")
```

---

## 17. 对用户回答时的建议口径

当用户问“代码放在哪里”：回答应指向 `AstrBot/data/plugins/<插件名>/main.py` 的插件类内部。

当用户问“管理员 ID 指什么”：区分机器人账号、平台账号、AstrBot WebUI 管理员、插件权限过滤中的管理员。插件里的 `PermissionType.ADMIN` 通常与 AstrBot 配置/平台适配识别到的管理员权限相关，不是插件类名，也不一定是机器人自身账号。

当用户问“插件能不能调用插件”：优先说明没有通用稳定的“插件直接调用另一个插件内部函数”的公共契约；推荐用公共服务层、HTTP API、事件/消息机制、共享存储或抽公共 Python 包实现解耦。若目标插件暴露了明确 API，再按其 README 调用。

