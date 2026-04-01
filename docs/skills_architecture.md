# Skills 架构说明

当前项目已经引入 `chat_app/skills/` 作为 agent 能力组织层。

## 目标

`skills` 的目标是把底层工具和规则按业务场景分组，再按上下文动态暴露给 agent。

这样做是因为 OneBot / NapCat 底层接口很多，如果直接全部暴露成 tools，会让模型更难选对工具，也会让 prompt 噪音越来越大。

## 当前分层

### 1. OneBot API 层

- `onebot_gateway/transport/client.py`

职责：

- 封装 NapCat / OneBot action API
- 不直接面向 agent

### 2. Skill 层

- `chat_app/skills/`

职责：

- 按领域组合 tools
- 给当前场景提供规则文本
- 控制哪些能力在当前上下文启用

### 3. Service / Session 层

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
    contact_discovery/
      skill.py
    message_state/
      skill.py
      tools.py
      types.py
    group_moderation/
      skill.py
      tools.py
      types.py
    friend_management/
      skill.py
      tools.py
      types.py
    account_profile/
      skill.py
      tools.py
      types.py
    account_status/
      skill.py
      tools.py
      types.py
    friend_request_management/
      skill.py
      tools.py
      types.py
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

### `contact_discovery`

只在私聊、发送者属于受信操作员且当前支持实时 OneBot 查询时启用。

提供：

- `lookup_contacts`
- `get_contact_profile`

### `group_inspection`

在私聊或群聊中启用（需 sender 且允许实时 OneBot 查询）。

提供：

- `get_group_list`
- `get_group_detail`
- `get_group_member_list`

### `message_state`

只在私聊且发送者属于受信操作员时启用。

提供：

- `mark_conversation_read`

### `friend_management`

只在私聊且发送者属于受信操作员时启用。

提供：

- `send_like`
- `delete_friend`

### `account_profile`

只在私聊且发送者属于受信操作员时启用。

提供：

- `set_qq_profile`
- `set_self_longnick`
- `set_qq_avatar`

### `account_status`

只在私聊且发送者属于受信操作员时启用。

提供：

- `set_online_status`
- `set_diy_online_status`

### `friend_request_management`

只在私聊且发送者属于受信操作员时启用。

提供：

- `set_friend_add_request`

## 运行时流程

```text
OneBot event
  -> ChatService
  -> build SkillContext
  -> SkillRegistry.resolve(context)
  -> 获得 runtime tools + runtime rules
  -> ChatSession.ask(..., runtime_tools=..., runtime_rules=...)
  -> 模型在当前 skill 范围内调用工具
  -> service 层执行结构化命令并做权限校验
```

## 后续建议

下一步可以继续做：

1. 增加长期记忆读取 skill
2. 增加更多 operator-only 的账号/好友管理能力
3. 把部分细粒度 tools 收敛成更高层的 domain tools
