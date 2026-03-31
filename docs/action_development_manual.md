# Action 开发手册

这份手册面向维护者，说明当前仓库里 action 的设计原则、开发流程和代码规范。

## 1. 目标

action 的目标不是让模型直接操作 OneBot，而是让模型先表达一个明确、可校验、可审计的动作意图，再由服务层决定是否真的执行。

## 2. 核心原则

### 2.1 分层职责

- `tool`：负责定义模型可调用的动作接口。
- `PendingAction`：负责承载待执行动作的数据。
- `ChatSession`：负责从 tool 输出中提取待执行动作。
- `ChatService`：负责权限判断、OneBot API 调用和执行结果落地。
- `OneBotWebSocketClient`：负责具体 action API 请求。

### 2.2 不要在 tool 里直接执行外部动作

禁止在 LangChain tool 中直接：

- 调 OneBot API
- 改数据库
- 写文件
- 执行不可逆副作用

tool 只能返回结构化命令。

### 2.3 权限一定放在服务层

权限规则不能依赖：

- 模型自觉
- prompt 提示
- 前端限制

最终必须在 `onebot_gateway/app/service.py` 校验。

### 2.4 按业务分类组织 action

当前推荐结构：

- `chat_app/actions/group_management/`
- `chat_app/actions/friend_management/`
- `chat_app/actions/profile/`

不要再回到一个目录下堆很多平铺文件。

## 3. 当前 Group Management Action 一览

目录：`chat_app/actions/group_management/`

### 3.1 已有 action

- `mute_group_member`
- `set_group_admin`
- `kick_group_member`
- `set_group_card`
- `set_group_special_title`

### 3.2 当前权限规则

| action | owner | admin | member |
|---|---|---|---|
| `mute_group_member` | 可操作 admin/member | 可操作 member | 不可操作 |
| `kick_group_member` | 可操作 admin/member | 可操作 member | 不可操作 |
| `set_group_card` | 可改 admin/member | 可改 member | 不可操作 |
| `set_group_admin` | 可设置/取消管理员 | 不可操作 | 不可操作 |
| `set_group_special_title` | 可设置/清空头衔 | 不可操作 | 不可操作 |

说明：

- “可操作”默认指只能操作低于自身角色的对象。
- `set_group_admin` 这类高风险动作不要复用通用权限规则。

## 4. 新增 action 的标准流程

### 第一步：确认接口

先在 `docs/napcat.md` 查清楚：

- action 名称
- 参数名
- 参数类型
- 语义边界

如果文档不清楚，不要拍脑袋命名。

### 第二步：决定分类

先判断这个 action 属于哪一类：

- 群管理
- 好友管理
- 资料设置
- 其他

然后放入对应目录。

### 第三步：增加 PendingAction 类型

位置：`chat_app/actions/<category>/types.py`

要求：

- 用 `@dataclass(frozen=True)`
- `to_dict()` 中必须有稳定的 `action` 字段
- 只保留执行必需参数

### 第四步：增加 tool

位置：`chat_app/actions/<category>/tools.py`

要求：

- 用 `@tool`
- 返回 JSON 字符串
- 文档字符串要写清参数含义和权限限制
- 做轻量参数归一化，不做真实执行

### 第五步：注册 tool

位置：`chat_app/tools/registry.py`

要求：

- 显式导入
- 显式 `append`
- 不做隐式扫描注册

### 第六步：解析 tool 输出

位置：`chat_app/chat.py`

要求：

- 校验 `tool_name`
- 校验 `action` 字段
- 再构造对应 `PendingAction`
- 解析失败时静默忽略，不要让整个会话崩掉

### 第七步：封装 OneBot 客户端 API

位置：`onebot_gateway/transport/client.py`

要求：

- 方法名与业务语义一致
- 请求参数尽量和 NapCat 文档一致
- `group_id` / `user_id` 统一转字符串，延续现有风格

### 第八步：服务层执行

位置：`onebot_gateway/app/service.py`

要求：

- 在 `ChatMessageSender` 协议补方法
- 在 `_execute_pending_actions()` 增加分发
- 新增 `_execute_xxx_action()`
- 权限失败要返回明确 `ActionResult`

### 第九步：补 prompt 提示

位置：`onebot_gateway/app/service.py` 的 `_build_model_input()`

要求：

- 告诉模型可以调用什么工具
- 告诉模型必要参数是什么
- 告诉模型大致权限边界

注意：这只是辅助，不替代服务层权限校验。

### 第十步：补测试

位置：`tests/test_moderation_actions.py`

至少补：

- `PendingAction` 的 `to_dict()` 测试
- tool 输出 JSON 测试
- 成功执行测试
- 权限拒绝测试

## 5. 权限设计建议

### 5.1 低风险群管动作

适合复用“高角色操作低角色”的动作：

- 禁言
- 踢人
- 改名片

这类动作可以继续使用 `_can_operate()` 风格的规则。

### 5.2 高风险动作

需要单独规则：

- 设置管理员
- 设置头衔
- 后续如果加“解散群”“转让群主”这类，也必须单独处理

原则：

- 权限越高，规则越具体
- 不要复用过于宽泛的通用逻辑

## 6. 当前推荐的代码风格

- 一个 action 对应一个 `Pending*Action`
- 一个 action 对应一个 tool 函数
- 一个 action 对应一个服务层执行函数
- 解析逻辑统一放在 `ChatSession._try_parse_pending_action()`
- 服务执行统一放在 `ChatService._execute_pending_actions()` 分发

## 7. 不要做的事

- 不要让 tool 直接调用 OneBot API
- 不要把权限判断写在 prompt 里就算结束
- 不要把很多不相关 action 混进一个平铺模块
- 不要为了省代码把高风险动作复用低风险权限规则
- 不要跳过测试

## 8. 新增 action 自检清单

提交前检查：

- NapCat 接口名和参数是否已核对
- action 是否放到了正确分类目录
- `PendingAction` 是否有稳定 `action` 字段
- tool 是否只返回 JSON，不直接执行副作用
- `ChatSession` 是否已解析新 action
- `OneBotWebSocketClient` 是否已补 API 方法
- `ChatService` 是否已补执行逻辑和权限规则
- prompt 是否已补工具说明
- 测试是否覆盖成功和拒绝场景
- 全量测试是否通过

## 9. 相关文档

- 扩展指南：`docs/action_extension_guide.md`
- NapCat 接口：`docs/napcat.md`
