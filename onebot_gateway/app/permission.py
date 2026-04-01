"""权限校验。"""

from __future__ import annotations

from onebot_gateway.app.types import ActionResult


class PermissionChecker:
    """检查用户是否有权限执行特定 action。"""

    def __init__(
        self,
        trusted_operator_ids: tuple[int, ...],
        trusted_actions: set[str] | None = None,
    ) -> None:
        self._trusted_operator_ids = set(trusted_operator_ids)
        self._trusted_actions = trusted_actions or {
            "send_like",
            "delete_friend",
            "set_qq_profile",
            "set_self_longnick",
            "set_qq_avatar",
            "set_online_status",
            "set_diy_online_status",
            "set_friend_add_request",
            "mark_conversation_read",
        }

    def check(self, event: object, action_name: str) -> ActionResult | None:
        """检查权限。返回 None 表示允许，返回 ActionResult 表示拒绝。"""
        if action_name not in self._trusted_actions:
            return None

        is_private = getattr(event, "is_private_message", None)
        if callable(is_private) and not is_private():
            return ActionResult(
                action=action_name,
                success=False,
                message="权限不足：该技能仅允许在私聊中由受信操作员使用。",
            )

        user_id = getattr(event, "user_id", None)
        if user_id is not None and int(user_id) in self._trusted_operator_ids:
            return None

        return ActionResult(
            action=action_name,
            success=False,
            message="权限不足：该技能仅允许受信操作员使用。",
        )
