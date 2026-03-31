# Skills 架构说明

当前项目已经引入 `chat_app/skills/` 作为 agent 能力组织层。

## 目标

`skills` 的目标不是替代 `actions`，而是把底层工具和规则按业务场景分组，再按上下文动态暴露给 agent。

这样做是因为 OneBot / NapCat 底层接口很多，如果直接全部暴露成 tools，会让模型更难选对工具，也会让 prompt 噪音越来越大。

## 当前分层

### 1. OneBot API 层

- `onebot_gateway/transport/client.py`

职责：

- 封装 NapCat / OneBot action API
- 不直接面向 agent

### 2. Action 层

- `chat_app/actions/group_management/`

职责：

- 定义结构化动作和原子工具
- 例如禁言、踢人、设管理员、改名片、改头衔

### 3. Skill 层

- `chat_app/skills/`

职责：

- 按领域组合 tools
- 给当前场景提供规则文本
- 控制哪些能力在当前上下文启用

### 4. Service / Session 层

- `onebot_gateway/app/service.py`
- `chat_app/chat.py`

职责：

- 根据消息场景生成 `SkillContext`
- 解析当前启用的 skills
- 将当前 skill 对应的 tools 和 rules 注入会话

## 当前目录

```text
chat_app/
  skills/
    __init__.py
    context.py
    registry.py
    types.py
    group_moderation/
      skill.py
    message_expression/
      skill.py
    memory_recall/
      skill.py
```

## 当前已有 skills

### `group_moderation`

只在群聊场景启用。

提供：

- `mute_group_member`
- `set_group_admin`
- `kick_group_member`
- `set_group_card`
- `set_group_special_title`

### `message_expression`

私聊和群聊都启用。

提供：

- `search_qq_emojis`

并提供富消息格式规则。

### `memory_recall`

私聊和群聊都启用。

当前先只提供规则，不直接提供 tool。

职责：

- 让模型注意保持与短期/长期记忆一致

## 运行时流程

```text
OneBot event
  -> ChatService
  -> build SkillContext
  -> SkillRegistry.resolve(context)
  -> 获得 runtime tools + runtime rules
  -> ChatSession.ask(..., runtime_tools=..., runtime_rules=...)
  -> 模型在当前 skill 范围内调用工具
  -> service 层执行 action 并做权限校验
```

## 为什么保留 actions

因为 `actions` 和 `skills` 不是一回事：

- `action` 是可执行动作
- `skill` 是面向 agent 的能力包

也就是说：

- `actions` 负责“系统能做什么”
- `skills` 负责“当前让 agent 知道什么、允许用什么”

## 后续建议

下一步可以继续做：

1. 增加 `friend_management` skill
2. 增加长期记忆读取 skill
3. 把部分细粒度 tools 收敛成更高层的 domain tools
