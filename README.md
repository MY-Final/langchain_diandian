点点的 langchain

## 项目说明

这是一个正在整理中的 Python 对话项目，当前包含两部分：

- `chat_app`：命令行对话入口
- `onebot_gateway`：连接 NapCat 并接收 OneBot WebSocket 事件

当前也已经支持通过 OneBot WebSocket action 发送消息。

`onebot_gateway` 当前按职责拆成两层：

- `transport/`：WebSocket 连接、事件接收、OneBot action 请求与发送消息
- `message/`：消息解析、消息段构造、触发判断、消息缓存、给 LangChain 的 adapter

## 环境准备

建议使用项目自带虚拟环境：

```bash
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

如果你已经激活了虚拟环境，也可以直接使用：

```bash
python -m pip install -r requirements.txt
```

## 环境变量

项目默认会读取根目录下的 `.env` 文件。

可以参考 `.env.example` 填写配置。

### 对话应用配置

```env
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=http://your-openai-compatible-host/v1
OPENAI_MODEL=your-model
SYSTEM_PROMPT_FILE=prompts/system_prompt.txt
CHAT_DEBUG_TOOL_CALLS=false
CHAT_MEMORY_ENABLE_SUMMARY=true
PRIVATE_CHAT_MEMORY_MAX_TURNS=12
PRIVATE_CHAT_MEMORY_SUMMARY_TRIGGER_TURNS=16
PRIVATE_CHAT_MEMORY_SUMMARY_BATCH_TURNS=6
GROUP_CHAT_MEMORY_MAX_TURNS=8
GROUP_CHAT_MEMORY_SUMMARY_TRIGGER_TURNS=12
GROUP_CHAT_MEMORY_SUMMARY_BATCH_TURNS=4
CHAT_MEMORY_MAX_SUMMARY_CHARS=1200
CHAT_MEMORY_MAX_INPUT_CHARS=12000
```

记忆相关配置说明：

- `CHAT_MEMORY_ENABLE_SUMMARY`：是否启用滚动摘要
- `PRIVATE_CHAT_MEMORY_*`：私聊上下文窗口与摘要阈值
- `GROUP_CHAT_MEMORY_*`：群聊上下文窗口与摘要阈值
- `CHAT_MEMORY_MAX_SUMMARY_CHARS`：摘要最大字符数
- `CHAT_MEMORY_MAX_INPUT_CHARS`：单次送入模型的上下文字符上限

调试相关配置：

- `CHAT_DEBUG_TOOL_CALLS`：是否在控制台打印 LangChain tool 调用记录

### NapCat / OneBot 配置

```env
NAPCAT_WS_URL=ws://your-host:3001/
NAPCAT_TOKEN=
ONEBOT_BOT_NAME_PATTERNS=点点,bot
ONEBOT_REPLY_WITH_QUOTE=true
ONEBOT_REPLY_SPLIT_ENABLED=true
ONEBOT_REPLY_SPLIT_MAX_CHARS=180
ONEBOT_REPLY_SPLIT_MARKER=[SPLIT]
```

`ONEBOT_BOT_NAME_PATTERNS` 支持用英文逗号分隔多个正则，用于识别群消息里是否在直接叫 bot。

`ONEBOT_REPLY_WITH_QUOTE` 控制回复时是否自动引用原消息，默认 `true`。

`ONEBOT_REPLY_SPLIT_ENABLED` 控制是否启用分段回复；默认尽量单条发送。

`ONEBOT_REPLY_SPLIT_MAX_CHARS` 控制单条回复最大字符数；只有超长时才会安全切分。

`ONEBOT_REPLY_SPLIT_MARKER` 是显式分段标记；如果模型输出里带这个标记，系统会优先按它拆成多条消息发送。

## 启动方式

### 1. 启动命令行对话

交互模式：

```bash
python -m chat_app
```

单轮消息：

```bash
python -m chat_app --message "你好"
```

如果你希望显式使用项目虚拟环境：

```bash
.\.venv\Scripts\python.exe -m chat_app
```

### 2. 启动 OneBot WebSocket 接收

用于连接 NapCat，并打印收到的原始事件、解析后的 JSON、触发判断，以及私聊/群聊场景下的 LangChain 回复：

```bash
python -m onebot_gateway
```

如果你希望显式使用项目虚拟环境：

```bash
.\.venv\Scripts\python.exe -m onebot_gateway
```

## 当前状态

- `onebot_gateway` 当前会解析 OneBot 消息事件，并提取适合后续智能体使用的字段
- 当前已支持提取：文本内容、发送人、群号、私聊/群聊类型、是否 @ 自己、是否回复消息
- 当前已支持判断：是否群聊、是否私聊、是否 @ bot、是否通过 bot 名称正则触发、是否回复了 bot 自己、是否回复了一条 @ bot 或点名 bot 的消息、是否应该进入后续处理
- 当前已支持发送：群消息、私聊消息，发送内容使用 OneBot 消息段数组组织
- 当前已支持私聊和群聊接入 LangChain，并自动引用原消息回复
- 当前已支持私聊和群聊分开配置记忆窗口，超过阈值后对旧上下文做滚动摘要
- 当前已支持 LangChain 回复分段，默认尽量单条发送；只有显式 `[SPLIT]` 或超长时才拆分，第一段可选引用原消息
- 当前已支持 LangChain 通过标签语法发送混合消息，例如 @、图片、表情等
- 当前已支持模型通过显式 tool 调用触发群管理 action，例如禁言、设管理员、踢人、改名片、改头衔
- 后续可以在此基础上继续接消息过滤、消息发送和 LangChain 集成

当前送入模型的群聊上下文会包含：

- 消息时间
- 发送者昵称
- 群名片
- 群号和群名
- 当前消息文本

当前群聊触发 LangChain 的条件：

- `@ bot`
- 回复 bot 发出的消息
- 文本命中 `ONEBOT_BOT_NAME_PATTERNS` 中配置的 bot 名称正则

## 消息发送

`onebot_gateway.transport.client.OneBotWebSocketClient` 现在支持：

实际导入路径为 `onebot_gateway.transport.client.OneBotWebSocketClient`。

- `send_group_message(group_id, message)`
- `send_private_message(user_id, message)`

`message` 可以直接传字符串，也可以传消息段列表。

文本发送示例：

```python
await client.send_group_message(515587773, "你好")
```

多消息段示例：

```python
from onebot_gateway.message.builder import at_segment, text_segment
from onebot_gateway.transport.client import OneBotWebSocketClient

await client.send_group_message(
    515587773,
    [
        text_segment("你好 "),
        at_segment(10001),
        text_segment(" 看这里"),
    ],
)
```

如果后面要支持更多类型，可以继续使用：

- `reply_segment(message_id)`
- `image_segment(file)`
- `custom_segment(segment_type, **data)`

## Adapter

`onebot_gateway.message.adapter` 用来隔离 OneBot 协议细节和上层智能体。

- `build_agent_input(event, decision)`：把 OneBot 事件压平成更适合 LangChain 的输入结构
- `build_text_reply(text, reply_message_id=None)`：把上层回复文本转成 OneBot 消息段

后面接 LangChain 时，建议只在边界层接触 OneBot 原始结构，业务层尽量只使用 adapter 产出的对象。

## 富消息回复

LangChain 回复现在支持使用标签语法生成 OneBot 混合消息，不需要使用 CQ 码。

示例：

```text
你好 <at qq="123456" /> 请看这里
```

当前支持的标签：

- `@`：`<at qq="123456" />`
- QQ face 表情：`<face id="14" />`
- 图片：`<image file="https://example.com/a.png" />`
- 语音：`<record file="voice.mp3" />`
- 视频：`<video file="demo.mp4" />`
- markdown：`<markdown># 标题</markdown>`
- 联系人：`<contact type="qq" id="123456" />`
- 戳一戳：`<poke type="qq" id="123456" />`

注意：

- 如果模型不知道目标用户 ID、文件地址等必要参数，不应该编造标签
- 当前消息中如果已经 @ 了某人，系统会把这些用户 ID 一起带给模型，方便模型继续艾特对方

## 表情工具

当前已接入本地 QQNT 表情索引，LangChain 可以通过 tool 检索合适的 `face` 表情。

工具链路：

- `assets/qq_emoji/indexes/emoji_records.jsonl`
- Python 检索索引
- LangChain tool: `search_qq_emojis`
- 模型输出 `<face id="..." />`

当前策略：

- 只支持 `face` 表情
- 模型应保守使用表情
- 一条回复最多建议使用一个表情
- 选择表情前优先调用 `search_qq_emojis`

## Action 开发

当前 action 采用“tool 只产生命令，service 才真正执行命令”的结构。

已接入的群管理 action：

- `mute_group_member`
- `set_group_admin`
- `kick_group_member`
- `set_group_card`
- `set_group_special_title`

相关文档：

- `docs/action_extension_guide.md`
- `docs/action_development_manual.md`

## 测试

运行全部测试：

```bash
.\.venv\Scripts\python.exe -m unittest discover -s tests
```
