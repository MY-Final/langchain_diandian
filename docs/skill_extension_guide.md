## Skill 扩展指南

这份文档说明如何在当前仓库里新增一个 skill。

## 当前 skill 运行链路

1. `ChatService` 根据消息构造 `SkillContext`
2. `SkillRegistry.resolve(context)` 选出当前启用的 skill
3. skill 提供本次可用的 rules 和 tools
4. `ChatSession.ask()` 按本次 runtime 动态绑定 tools
5. service 层执行 tool 生成的结构化命令并做权限校验

## 最小扩展步骤

### 1. 新建 skill 目录

例如：

- `chat_app/skills/friend_management/`

### 2. 定义 tools

例如放在：

- `chat_app/skills/friend_management/tools.py`

### 3. 如果需要，定义数据类型

例如放在：

- `chat_app/skills/friend_management/types.py`

### 4. 定义 `skill.py`

最小结构：

```python
from chat_app.skills.context import SkillContext
from chat_app.skills.types import SkillSpec


def _applies_to(context: SkillContext) -> bool:
    return True


def _build_rules(_context: SkillContext) -> tuple[str, ...]:
    return ("- 这里写该 skill 的规则。",)


def _build_tools(_context: SkillContext) -> tuple:
    return ()


MY_SKILL = SkillSpec(
    name="my_skill",
    description="示例技能。",
    applies_to=_applies_to,
    build_rules=_build_rules,
    build_tools=_build_tools,
    priority=100,
)
```

### 5. 注册到 `chat_app/skills/registry.py`

把新 skill 加到默认 skill 列表里。

### 6. 如需执行副作用，补 service 层逻辑

如果 tool 会触发真实动作：

- 由 tool 返回结构化命令
- 再由 `onebot_gateway/app/service.py` 执行并校验权限

### 7. 补测试

至少补：

- skill 选择测试
- tool 输出测试
- service 执行测试

## 当前已有 skills

- `group_moderation`
- `message_expression`
- `memory_recall`
- `contact_discovery`
- `group_inspection`
- `message_state`
- `friend_management`
- `account_profile`
- `account_status`
- `friend_request_management`

## 受信操作员技能

像删好友、改资料这类高风险 skill，建议默认只在以下条件启用：

- 私聊场景
- 发送者 user_id 位于 `ONEBOT_OPERATOR_USER_IDS`

这样可以避免把机器人自身账号管理能力暴露给普通用户。

## 实时查询 skill

像 `contact_discovery` 这类 skill，不适合走“pending-command -> service 执行 -> 再回复”的模式。

这类 skill 应该：

- 由 skill 在运行时构造实时查询 tools
- 在当前模型推理轮次中直接把查询结果返回给模型
- 不进入 pending command 队列

## 一句话原则

**skill 负责组织能力，service 负责真正执行能力。**
