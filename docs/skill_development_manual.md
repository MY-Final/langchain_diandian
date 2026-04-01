# Skill 开发手册

这份手册面向维护者，说明当前仓库里 skill 的设计原则、开发流程和代码规范。

## 1. 目标

skill 的目标不是让模型直接操作 OneBot 底层接口，而是把某一类能力按场景组织成 agent 更容易理解和调用的能力包，再由服务层做最终执行和权限校验。

## 2. 当前分层

### 2.1 OneBot API 层

- `onebot_gateway/transport/client.py`

职责：

- 封装 NapCat / OneBot action API
- 不直接暴露给 agent

### 2.2 Skill 层

- `chat_app/skills/`

职责：

- 定义 agent 当前可用的能力包
- 组合该能力包需要的 tools
- 提供该能力包的规则文本

### 2.3 Service 层

- `onebot_gateway/app/service.py`

职责：

- 根据消息场景选择 skill
- 做最终权限校验和执行

## 3. 当前目录结构

当前推荐结构：

- `chat_app/skills/contact_discovery/`
- `chat_app/skills/message_state/`
- `chat_app/skills/group_moderation/`
- `chat_app/skills/friend_management/`
- `chat_app/skills/account_profile/`
- `chat_app/skills/account_status/`
- `chat_app/skills/friend_request_management/`
- `chat_app/skills/message_expression/`
- `chat_app/skills/memory_recall/`

基础设施位于：

- `chat_app/skills/context.py`
- `chat_app/skills/types.py`
- `chat_app/skills/registry.py`

## 4. 当前已有 skills

### `group_moderation`

提供：

- `mute_group_member`
- `set_group_admin`
- `kick_group_member`
- `set_group_card`
- `set_group_special_title`

### `message_expression`

提供：

- `search_qq_emojis`

### `memory_recall`

当前先提供记忆一致性规则，不直接提供 tool。

### `contact_discovery`

提供：

- `lookup_contacts`
- `get_contact_profile`

默认仅在私聊、发送者属于 `ONEBOT_OPERATOR_USER_IDS` 且当前支持实时 OneBot 查询时启用。

这类 skill 通常不是 pending-command，而是需要把实时查询结果直接回填给模型。

### `message_state`

提供：

- `mark_conversation_read`

默认仅在私聊且发送者属于 `ONEBOT_OPERATOR_USER_IDS` 时启用。

### `friend_management`

提供：

- `send_like`
- `delete_friend`

默认仅在私聊且发送者属于 `ONEBOT_OPERATOR_USER_IDS` 时启用。

### `account_profile`

提供：

- `set_qq_profile`
- `set_self_longnick`
- `set_qq_avatar`

默认仅在私聊且发送者属于 `ONEBOT_OPERATOR_USER_IDS` 时启用。

### `account_status`

提供：

- `set_online_status`
- `set_diy_online_status`

默认仅在私聊且发送者属于 `ONEBOT_OPERATOR_USER_IDS` 时启用。

### `friend_request_management`

提供：

- `set_friend_add_request`

默认仅在私聊且发送者属于 `ONEBOT_OPERATOR_USER_IDS` 时启用。

### `group_inspection`

提供：

- `get_group_list`
- `get_group_detail`
- `get_group_member_list`

默认在私聊/群聊中启用（需 sender 且允许实时 OneBot 查询）。

这类 skill 属于实时查询，查询结果当轮直接回填给模型，不走 pending-command。

## 5. 新增 skill 的标准流程

### 第一步：决定 skill 分类目录

例如：

- `chat_app/skills/group_moderation/`
- `chat_app/skills/friend_management/`
- `chat_app/skills/profile/`

### 第二步：定义 skill 的 tools 和数据类型

位置建议：

- `chat_app/skills/<category>/tools.py`
- `chat_app/skills/<category>/types.py`

要求：

- tool 返回结构化 JSON
- 不直接执行不可逆副作用
- 需要的数据类型放到该 skill 自己目录里

### 第三步：定义 skill 规则和启用条件

位置：`chat_app/skills/<category>/skill.py`

一个 skill 至少应定义：

- `applies_to(context)`
- `build_rules(context)`
- `build_tools(context)`
- `SkillSpec(...)`

### 第四步：注册到 `SkillRegistry`

位置：`chat_app/skills/registry.py`

要求：

- 显式注册
- 按优先级排序
- 不做隐式扫描

### 第五步：补 service 层执行逻辑

位置：`onebot_gateway/app/service.py`

要求：

- tool 只是生成结构化命令
- service 层必须做最终权限校验
- 权限失败要给出明确错误

### 第六步：补测试

至少补：

- skill 选择测试
- tool 输出测试
- service 执行测试
- 权限拒绝测试

## 6. 权限设计原则

- 权限校验必须留在 service 层
- 高风险能力不要只靠 prompt 提示
- 不同 skill 可以有不同权限模型

例如：

- `group_moderation` 中禁言/踢人可以复用高角色操作低角色
- 设置管理员、设置头衔这类高风险动作要单独收紧
- 账号资料、好友管理这类技能要默认限制为受信操作员

## 7. 不要做的事

- 不要把所有 OneBot 底层接口都直接暴露给 agent
- 不要让 tool 直接调用 OneBot API
- 不要把所有规则塞进一个大 prompt 而不分 skill
- 不要为了省代码把高风险权限规则复用成宽泛通用规则

## 8. 自检清单

新增 skill 前后检查：

- skill 是否放在正确目录
- tool 是否只负责产生命令
- rules 是否写清楚场景和限制
- 如为高风险私聊技能，是否限制为受信操作员
- `SkillRegistry` 是否正确启用/禁用该 skill
- service 是否补了权限和执行逻辑
- 测试是否覆盖成功和拒绝场景

## 9. 相关文档

- 扩展指南：`docs/skill_extension_guide.md`
- 架构说明：`docs/skills_architecture.md`
- NapCat 接口：`docs/napcat.md`
