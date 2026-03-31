点点的 langchain

## 项目说明

这是一个正在整理中的 Python 对话项目，当前包含两部分：

- `chat_app`：命令行对话入口
- `onebot_gateway`：连接 NapCat 并接收 OneBot WebSocket 事件

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
```

### NapCat / OneBot 配置

```env
NAPCAT_WS_URL=ws://your-host:3001/
NAPCAT_TOKEN=
```

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

用于连接 NapCat，并打印收到的原始事件和解析后的 JSON：

```bash
python -m onebot_gateway
```

如果你希望显式使用项目虚拟环境：

```bash
.\.venv\Scripts\python.exe -m onebot_gateway
```

## 当前状态

- `onebot_gateway` 当前只负责连接 NapCat 并打印消息
- 这一阶段还没有把 OneBot 消息转给 LangChain
- 后续可以在此基础上继续接消息过滤、消息发送和 LangChain 集成

## 测试

运行全部测试：

```bash
.\.venv\Scripts\python.exe -m unittest discover -s tests
```
