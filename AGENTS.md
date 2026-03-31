# AGENTS.md

为在 `C:\Users\EDY\langchain` 中工作的编码代理提供说明。
本文档基于当前仓库的实际状态编写。

## 适用范围
- 适用于整个仓库。
- 创建本文档前，根目录下不存在 `AGENTS.md`。
- 未发现 `.cursor/rules/` 中存在 Cursor 规则。
- 未发现 `.cursorrules` 文件。
- 未发现 `.github/copilot-instructions.md` 中存在 Copilot 说明。

## 仓库概览
- 当前仓库是一个小型 Python 对话示例项目。
- 顶层入口文件是 `test.py`。
- 核心源码位于 `chat_app/`。
- 测试文件位于 `tests/`。
- 本地虚拟环境位于 `.venv/`。
- 已存在 `requirements.txt`，当前显式依赖是 `langchain-openai`。
- 未发现 `pyproject.toml`、`setup.cfg`、`tox.ini`、`pytest.ini` 或 `Makefile`。
- 当前仍未发现仓库级别的 lint、formatter 或 type checker 配置。

## 通用工作规则
- 在新增配置文件之前，将该仓库视为以脚本为主的 Python 项目。
- 优先做小而精确的修改，避免大范围重构。
- 保持现有示例可以继续运行。
- 不要假设仓库已经具备打包、CI 或发布流程。
- 不要把 `.venv/` 或 `.idea/` 当作源码目录。

## 标准命令
所有命令都应在仓库根目录 `C:\Users\EDY\langchain` 下执行。

### 环境
- Windows 激活命令：`.venv\Scripts\activate`
- 直接使用解释器：`.venv\Scripts\python.exe`
- 如果虚拟环境已激活，也可以直接使用 `python`。

### 安装依赖
- 使用：`.venv\Scripts\python.exe -m pip install -r requirements.txt`

### 运行 / 冒烟验证
- 交互式对话：`.venv\Scripts\python.exe test.py`
- 单轮对话：`.venv\Scripts\python.exe test.py --message "你好"`
- 激活虚拟环境后的等价命令：`python test.py`

### 构建
- 当前没有单独配置构建步骤。
- 对这个仓库来说，最接近“构建”的行为是安装依赖并完成一次对话冒烟验证。
- 使用：`.venv\Scripts\python.exe test.py --message "你好"`

### Lint
- 当前没有配置 lint 工具。
- 本地虚拟环境中未安装 `ruff`。
- 不要把臆造出来的 lint 命令写成项目既有规范。

### 格式化
- 当前没有配置 formatter。
- 本地虚拟环境中未安装 `black`。
- 在没有新增 formatter 之前，应手动保持现有风格一致。

### 测试
- 当前使用标准库 `unittest`。
- 本地虚拟环境中未安装 `pytest`。
- 运行全部测试：`.venv\Scripts\python.exe -m unittest discover -s tests`
- 当前可用的额外运行验证命令：`.venv\Scripts\python.exe test.py --message "你好"`

### 运行单个测试
- 当前单测命令优先使用 `unittest` 模块路径。
- 运行单个测试模块：`.venv\Scripts\python.exe -m unittest tests.test_config`
- 运行单个测试类或方法：`.venv\Scripts\python.exe -m unittest tests.test_config.LoadDotenvFileTests.test_loads_missing_environment_values_only`
- 如果后续引入 `pytest`，优先使用：
  - `.venv\Scripts\python.exe -m pytest tests/test_file.py::test_name`
- 在依赖未实际加入前，不要声称 `pytest` 可用。

## 代码风格

### 导入
- 导入顺序按以下分组：标准库、第三方、本地模块。
- 分组之间使用一个空行分隔。
- 优先使用显式导入，不使用通配符导入。
- 只导入实际使用的内容。
- 除非有明确的惰性加载理由，否则导入应放在模块顶部。

### 格式化
- 遵循常规 PEP 8 约定。
- 使用 4 个空格缩进。
- 单行长度保持适中，目标约为 88-100 个字符。
- 文件末尾保留换行。
- 避免行尾空白。
- 优先保证结构简单易读，不要为了压缩代码牺牲可读性。

### 类型
- 新增函数和修改过的函数签名应添加类型标注。
- 保留已有的类型标注。
- 在可行时优先使用具体类型，而不是宽泛的 `Any`。
- 对可选值或失败状态，使用 `None`、异常或结构化返回值显式表达。
- 让函数契约能从签名上直接看出来。

### 命名
- 函数、变量、辅助方法使用 `snake_case`。
- 类名使用 `PascalCase`。
- 常量使用 `UPPER_SNAKE_CASE`。
- 优先使用有描述性的名称，不要过度缩写。
- 除非作用域极小且含义非常清晰，否则避免使用 `data`、`obj`、`temp` 之类模糊命名。

### 函数与模块
- 函数应尽量小，并只承担一个明确职责。
- 只有在重复逻辑真实出现时再提取辅助函数。
- 如果脚本继续增长，优先引入 `main()` 入口，而不是增加更多顶层执行逻辑。
- 副作用应尽量放在程序边界。
- 优先通过显式参数传递依赖，而不是依赖隐藏的全局状态。

### 错误处理
- 失败时应给出清晰、具体的错误。
- 抛出或捕获尽可能窄的异常类型。
- 不要静默吞掉异常。
- 错误信息中应包含可操作的上下文。
- 对外部输入在使用前进行校验。
- 调用模型或网络服务时，要预期认证失败、超时、接口返回结构变化等问题。

### 输出与日志
- 输出应有明确目的，避免噪声。
- 不要把临时调试打印留在提交代码中。
- 如果确实需要日志，优先使用 `logging`，不要随意散落 `print`。

## LangChain 相关说明
- 当前项目通过 `langchain-openai` 的 `ChatOpenAI` 连接 OpenAI 兼容接口。
- 工具函数应尽量小、确定性强、易于检查。
- 工具函数应有清晰的签名和文档字符串。
- Prompt 字符串应保持明确，并尽量放在使用位置附近。
- 工具函数的返回值优先保持简单、可序列化。
- 避免在 agent 初始化或调用代码中引入隐藏副作用。
- 配置优先从环境变量或 `.env` 读取，不要把密钥硬编码到源码中。

## 语言说明
- 现有代码中已经包含中文文档字符串和面向用户的中文文本。
- 修改相邻内容时，保持周围文本的语言一致。
- 除非任务明确要求，否则不要翻译现有产品文案。
- 新增面向开发者的文档默认使用中文或与现有文档保持一致；当前文件已采用中文。

## 面向代理的测试要求
- 修改代码后，运行当前能做到的最小有效验证。
- 目前通常至少执行：`.venv\Scripts\python.exe -m unittest discover -s tests`
- 如果改动涉及真实模型调用，再补充执行：`.venv\Scripts\python.exe test.py --message "你好"`
- 如果新增了可复用逻辑，优先考虑补充真实测试模块，而不只是依赖手动执行。
- 如果引入了测试框架，请同步更新本文档中的准确命令。

## 依赖管理说明
- 不要随意新增依赖。
- 如果标准库能满足需求，优先使用标准库。
- 如果必须新增第三方包，需要说明新增原因。
- 未来如果加入依赖管理文件，应将本文档中的推断性说明替换为精确命令。

## 默认应避免触碰的区域
- `.venv/`
- `.idea/`
- 生成文件或环境相关文件，除非任务明确要求修改。

## 何时应更新本文档
- 当仓库新增真实的 build、lint、format 或 test 工具时。
- 当源码从 `test.py` 扩展为包结构或加入 `tests/` 目录时。
- 当仓库新增 Cursor 或 Copilot 指令文件时。
- 当仓库规范从“基于推断”变为“基于配置”时。

## 给代理的实用摘要
- 最稳妥的解释器是 `.venv\Scripts\python.exe`。
- 当前可运行入口是 `test.py`，核心源码目录是 `chat_app/`。
- 默认认为仓库没有正式构建流水线。
- 默认认为仓库没有配置 lint 或 formatter。
- 当前已有基于 `unittest` 的基础测试。
- 代码修改应保持小而清晰，并尽量带上类型信息。
