## Action 扩展指南

这份文档说明如何在当前仓库里新增一个 OneBot action。

当前已经接入的 action 只有一个：`mute_group_member`。
它的链路是：

1. 模型显式调用 LangChain tool。
2. tool 不直接执行 API，只返回一个 `PendingAction` JSON。
3. `ChatSession` 解析这个 JSON，收集到待执行 action。
4. `ChatService` 在回复前执行 action，并做权限校验。

这样做的好处是：

- tool 层保持纯函数，容易测。
- 真正的 OneBot 调用集中在服务层，便于加权限和审计。
- 模型只有“显式调用 tool”时才会触发动作。

---

## 当前涉及的目录

新增一个 action，通常只需要改这几个地方：

- `chat_app/actions/<category>/types.py`
  这里定义某一类 action 的待执行数据结构。
- `chat_app/actions/<category>/tools.py`
  这里定义某一类 action 的 LangChain tool。
- `chat_app/tools/registry.py`
  在这里注册 tool。
- `chat_app/chat.py`
  在这里把 tool 返回的 JSON 解析成待执行 action。
- `onebot_gateway/transport/client.py`
  如果 OneBot API 还没封装，需要先加客户端方法。
- `onebot_gateway/app/service.py`
  在这里真正执行 action，并加权限校验。
- `tests/test_moderation_actions.py`
  给 action 和执行链路补测试。

---

## 最小扩展步骤

以“设置管理员”为例，建议按下面 6 步做。

### 1. 先决定 action 分类目录

当前建议按业务分类放子目录，例如：

- `chat_app/actions/group_management/`
- `chat_app/actions/friend_management/`
- `chat_app/actions/profile/`

像禁言、设置管理员、踢人，都应该继续放在：

- `chat_app/actions/group_management/types.py`
- `chat_app/actions/group_management/tools.py`

### 2. 在分类目录的 `types.py` 增加 PendingAction 类型

参考现有的 `PendingMuteAction`，新增一个数据类：

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

- `action` 字段必须稳定，后面靠它分发执行逻辑。
- 字段只保留执行所需的最小集合，不要塞多余上下文。

### 3. 在分类目录的 `tools.py` 新增 tool

例如：

```python
@tool
def set_group_admin(user_id: int, group_id: int, enable: bool = True) -> str:
    """设置或取消群管理员。

    调用后会生成一条待执行指令，由服务层校验权限并执行。
    - 仅群聊场景可用。
    - 一般只有群主 owner 可以设置管理员。
    """
    action = PendingSetGroupAdminAction(
        group_id=group_id,
        user_id=user_id,
        enable=enable,
    )
    return json.dumps(action.to_dict(), ensure_ascii=False)
```

约定：

- tool 只负责参数归一化。
- tool 不直接碰 OneBot 客户端。
- 返回值统一用 JSON 字符串，和现在的 mute 保持一致。

### 4. 在 `registry.py` 注册 tool

例如：

```python
from chat_app.actions.moderation import mute_group_member, set_group_admin

tools.append(mute_group_member)
tools.append(set_group_admin)
```

### 5. 在 `chat.py` 解析 tool 输出

当前 `ChatSession` 里已经有 `_try_parse_mute_action()`。
新增 action 时，按同样模式再加一个解析函数，或者把它改成通用分发。

最简单做法：

```python
def _try_parse_set_group_admin_action(self, tool_name: str, tool_output: str) -> None:
    if tool_name != "set_group_admin":
        return
    data = json.loads(tool_output)
    if not isinstance(data, dict) or data.get("action") != "set_group_admin":
        return
    self._pending_actions.append(
        PendingSetGroupAdminAction(
            group_id=int(data["group_id"]),
            user_id=int(data["user_id"]),
            enable=bool(data.get("enable", True)),
        )
    )
```

然后在工具循环里调用它。

如果后面 action 多了，建议把：

- `_try_parse_mute_action()`

改成：

- `_try_parse_action()`

统一按 `action` 字段分发。

### 6. 在 OneBot 客户端补 API 封装

如果 NapCat / OneBot 有对应接口，就在 `onebot_gateway/transport/client.py` 增加方法。

例如未来可能长这样：

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

是否真叫 `set_group_admin`，要以 `docs/napcat.md` 为准。

### 7. 在 `ChatService` 中真正执行

这是最关键的一层。

现在的服务层是按 `PendingMuteAction` 直接执行的。新增动作时，建议照着现有结构继续扩：

1. 扩展 `ChatMessageSender` 协议。
2. 在 `_execute_pending_actions()` 里分发。
3. 给新 action 写单独执行函数。

例如：

```python
async def _execute_set_group_admin(
    self,
    sender: ChatMessageSender,
    action: PendingSetGroupAdminAction,
    bot_user_id: int | None,
) -> ActionResult:
    if bot_user_id is None:
        return ActionResult(
            action="set_group_admin",
            success=False,
            message="无法确认机器人身份。",
        )

    bot_info = await sender.get_group_member_info(action.group_id, bot_user_id)
    if bot_info is None:
        return ActionResult(
            action="set_group_admin",
            success=False,
            message="无法获取机器人自身群成员信息。",
        )

    bot_role = str(bot_info.get("role", "member"))
    if bot_role != "owner":
        return ActionResult(
            action="set_group_admin",
            success=False,
            message="权限不足：只有群主可设置管理员。",
        )

    await sender.set_group_admin(action.group_id, action.user_id, action.enable)
    return ActionResult(
        action="set_group_admin",
        success=True,
        message="已设置群管理员。" if action.enable else "已取消群管理员。",
    )
```

---

## 推荐的权限设计

不是所有动作都用同一套权限规则。

### 适合复用 `_can_operate()` 的动作

- 禁言
- 踢人
- 改头衔

这类动作通常是“高角色操作低角色”。

### 不适合直接复用 `_can_operate()` 的动作

- 设置管理员
- 解管理员

这类动作通常应该更严格，建议单独写规则。

对“设置管理员”，建议默认规则：

- 只有 `owner` 可以设置或取消管理员。
- `admin` 不允许设置管理员。
- `member` 不允许设置管理员。

---

## 给“设置管理员”最少要改的文件

如果你现在就要加这个 action，最少会改这些文件：

1. `chat_app/actions/group_management/types.py`
2. `chat_app/actions/group_management/tools.py`
3. `chat_app/tools/registry.py`
4. `chat_app/chat.py`
5. `onebot_gateway/transport/client.py`
6. `onebot_gateway/app/service.py`
7. `tests/test_moderation_actions.py`

---

## 复制模板

你可以直接按这个顺序复制一份来加新 action：

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
def _try_parse_xxx_action(self, tool_name: str, tool_output: str) -> None:
    if tool_name != "xxx_tool":
        return
    data = json.loads(tool_output)
    if not isinstance(data, dict) or data.get("action") != "xxx":
        return
    self._pending_actions.append(PendingXXXAction(...))
```

### E. 服务层执行

```python
async def _execute_xxx_action(...) -> ActionResult:
    # 权限校验
    # OneBot API 调用
    return ActionResult(action="xxx", success=True, message="执行成功")
```

### F. 测试

至少补这 3 类：

- tool 输出测试
- 权限测试
- 服务层执行测试

---

## 当前实现的一个注意点

现在 `ChatService` 和 `ChatSession` 还是偏“单动作类型”风格：

- `PendingMuteAction`
- `_try_parse_mute_action()`

这对于 1 到 2 个 action 很够用，也最直接。

现在已经按分类目录组织 action；后面新增时，优先先判断应该归到哪个分类目录，再按相同模式扩展。

---

## 一句话原则

新增 action 时，记住这条：

**tool 只产生命令，service 才真正执行命令。**

如果你要，我下一步可以直接把“设置管理员 action”按这份文档落到代码里。
