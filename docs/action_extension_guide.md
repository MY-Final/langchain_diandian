## Action 扩展指南

这份文档说明如何在当前仓库里新增一个 OneBot action。

当前 action 的执行链路是：

1. 模型显式调用 LangChain tool。
2. tool 不直接执行 OneBot API，只返回一个 `PendingAction` JSON。
3. `ChatSession` 解析这个 JSON，收集到待执行 action。
4. `ChatService` 在回复前执行 action，并做权限校验。

这样做的好处是：

- tool 层保持纯函数，容易测试。
- 真正的 OneBot 调用集中在服务层，便于统一做权限和审计。
- 模型只有显式调用 tool 时才会触发动作。

---

## 当前目录结构

当前建议按业务分类组织 action：

- `chat_app/actions/group_management/types.py`
- `chat_app/actions/group_management/tools.py`
- `chat_app/tools/registry.py`
- `chat_app/chat.py`
- `onebot_gateway/transport/client.py`
- `onebot_gateway/app/service.py`
- `tests/test_moderation_actions.py`

其中：

- `types.py` 定义待执行 action 数据结构。
- `tools.py` 定义 LangChain tool。
- `registry.py` 注册 tool。
- `chat.py` 解析 tool 输出。
- `client.py` 封装 OneBot action API。
- `service.py` 真正执行 action，并做权限判断。

---

## 当前已接入的 Group Management Action

当前 `chat_app/actions/group_management/` 已包含：

- `mute_group_member`
- `set_group_admin`
- `kick_group_member`
- `set_group_card`
- `set_group_special_title`

---

## 当前权限矩阵

### 可复用“高角色操作低角色”规则的动作

- `mute_group_member`
- `kick_group_member`
- `set_group_card`

默认规则：

- `owner` 可操作 `admin/member`
- `admin` 可操作 `member`
- `member` 不可操作他人

### 需要更严格单独规则的动作

- `set_group_admin`
- `set_group_special_title`

默认规则：

- `set_group_admin`：只有 `owner` 可设置/取消管理员
- `set_group_special_title`：只有 `owner` 可设置/清空头衔

注意：

- 不要为了省事把所有动作都套用 `_can_operate()`。
- 高风险动作优先单独写权限规则。

---

## 最小扩展步骤

### 1. 先决定 action 归属哪个分类目录

例如：

- 群管理：`chat_app/actions/group_management/`
- 好友管理：`chat_app/actions/friend_management/`
- 资料设置：`chat_app/actions/profile/`

如果是禁言、踢人、改名片、改头衔，就继续放在 `group_management/`。

### 2. 在分类目录的 `types.py` 增加 PendingAction

例如新增一个 action：

```python
@dataclass(frozen=True)
class PendingSetGroupAdminAction:
    group_id: int
    user_id: int
    enable: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "set_group_admin",
            "group_id": self.group_id,
            "user_id": self.user_id,
            "enable": self.enable,
        }
```

约定：

- `action` 字段必须稳定。
- 字段只保留执行所需的最小集合。
- 不要把推理上下文塞进 pending action。

### 3. 在分类目录的 `tools.py` 新增 tool

例如：

```python
@tool
def set_group_admin(user_id: int, group_id: int, enable: bool = True) -> str:
    action = PendingSetGroupAdminAction(
        group_id=group_id,
        user_id=user_id,
        enable=enable,
    )
    return json.dumps(action.to_dict(), ensure_ascii=False)
```

约定：

- tool 只负责参数归一化和返回 JSON。
- tool 不直接调用 OneBot API。
- tool 文档字符串里要写清楚权限边界和参数语义。

### 4. 在 `registry.py` 注册 tool

例如：

```python
from chat_app.actions.group_management import mute_group_member, set_group_admin

tools.append(mute_group_member)
tools.append(set_group_admin)
```

### 5. 在 `chat.py` 解析 tool 输出

当前实现已经是统一的 `_try_parse_pending_action()` 分发模式。

例如：

```python
if tool_name == "set_group_admin" and action_name == "set_group_admin":
    self._pending_actions.append(
        PendingSetGroupAdminAction(
            group_id=int(data["group_id"]),
            user_id=int(data["user_id"]),
            enable=bool(data.get("enable", True)),
        )
    )
    return
```

### 6. 在 OneBot 客户端补 API 封装

例如：

```python
async def set_group_admin(
    self, group_id: int | str, user_id: int | str, enable: bool = True
) -> dict[str, Any]:
    return await self.request(
        "set_group_admin",
        {
            "group_id": str(group_id),
            "user_id": str(user_id),
            "enable": enable,
        },
    )
```

接口名和字段必须以 `docs/napcat.md` 为准。

### 7. 在 `ChatService` 中执行 action

建议做法：

1. 扩展 `ChatMessageSender` 协议。
2. 在 `_execute_pending_actions()` 中分发。
3. 给新 action 写单独执行函数。

例如：

```python
async def _execute_set_group_admin_action(
    self,
    sender: ChatMessageSender,
    action: PendingSetGroupAdminAction,
    bot_user_id: int | None,
) -> ActionResult:
    ...
```

### 8. 补测试

至少补这 3 类：

- tool 输出测试
- 权限测试
- 服务层执行测试

---

## 复制模板

### A. 定义 PendingAction

```python
@dataclass(frozen=True)
class PendingXXXAction:
    field_a: int
    field_b: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "action": "xxx",
            "field_a": self.field_a,
            "field_b": self.field_b,
        }
```

### B. 定义 tool

```python
@tool
def xxx_tool(field_a: int, field_b: bool = True) -> str:
    action = PendingXXXAction(field_a=field_a, field_b=field_b)
    return json.dumps(action.to_dict(), ensure_ascii=False)
```

### C. 注册 tool

```python
tools.append(xxx_tool)
```

### D. 解析 tool 输出

```python
if tool_name == "xxx_tool" and action_name == "xxx":
    self._pending_actions.append(PendingXXXAction(...))
    return
```

### E. 服务层执行

```python
async def _execute_xxx_action(...) -> ActionResult:
    # 权限校验
    # OneBot API 调用
    return ActionResult(action="xxx", success=True, message="执行成功")
```

### F. 测试

- tool 输出测试
- 权限测试
- 服务层执行测试

---

## 一句话原则

**tool 只产生命令，service 才真正执行命令。**

更完整的开发规范见：`docs/action_development_manual.md`
