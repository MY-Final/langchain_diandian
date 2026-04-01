"""OneBot 应用服务共享类型。"""

from __future__ import annotations

from dataclasses import dataclass

from chat_app.chat import ToolCallTrace
from chat_app.skills.account_profile import (
    PendingSetQQAvatarAction,
    PendingSetQQProfileAction,
    PendingSetSelfLongNickAction,
)
from chat_app.skills.account_status import (
    PendingSetDIYOnlineStatusAction,
    PendingSetOnlineStatusAction,
)
from chat_app.skills.essence_message import (
    PendingAddEssenceMessageAction,
    PendingGetEssenceMessageListAction,
    PendingRemoveEssenceMessageAction,
)
from chat_app.skills.file_send import (
    PendingSendGroupFileMessageAction,
    PendingSendPrivateFileAction,
)
from chat_app.skills.forward_message import PendingSendForwardMessageAction
from chat_app.skills.friend_management import (
    PendingDeleteFriendAction,
    PendingSendLikeAction,
)
from chat_app.skills.friend_request_management import PendingSetFriendAddRequestAction
from chat_app.skills.group_announcement import (
    PendingGetGroupNoticeAction,
    PendingSendGroupNoticeAction,
)
from chat_app.skills.group_file import (
    PendingDeleteGroupFileAction,
    PendingGetGroupFilesAction,
    PendingUploadGroupFileAction,
)
from chat_app.skills.group_moderation import (
    PendingAction as PendingGroupModerationAction,
    PendingKickGroupMemberAction,
    PendingMuteAction,
    PendingSetGroupAdminAction,
    PendingSetGroupCardAction,
    PendingSetGroupSpecialTitleAction,
)
from chat_app.skills.message_recall import PendingRecallMessageAction
from chat_app.skills.message_state import PendingMarkConversationReadAction
from onebot_gateway.app.protocol import ChatMessageSender
from onebot_gateway.message.adapter import AgentInput


@dataclass
class ActionResult:
    """单条动作执行结果。"""

    action: str
    success: bool
    message: str

    def to_dict(self) -> dict[str, object]:
        return {"action": self.action, "success": self.success, "message": self.message}


@dataclass
class ChatHandleResult:
    """消息处理结果。"""

    should_reply: bool
    reply_text: str
    reply_parts: tuple[str, ...]
    tool_traces: tuple[ToolCallTrace, ...]
    agent_input: AgentInput
    action_results: tuple[ActionResult, ...] = ()


PendingCommand = (
    PendingGroupModerationAction
    | PendingSendLikeAction
    | PendingDeleteFriendAction
    | PendingSetQQProfileAction
    | PendingSetSelfLongNickAction
    | PendingSetQQAvatarAction
    | PendingSetOnlineStatusAction
    | PendingSetDIYOnlineStatusAction
    | PendingSetFriendAddRequestAction
    | PendingMarkConversationReadAction
    | PendingRecallMessageAction
    | PendingSendGroupNoticeAction
    | PendingGetGroupNoticeAction
    | PendingUploadGroupFileAction
    | PendingGetGroupFilesAction
    | PendingDeleteGroupFileAction
    | PendingAddEssenceMessageAction
    | PendingGetEssenceMessageListAction
    | PendingRemoveEssenceMessageAction
    | PendingSendPrivateFileAction
    | PendingSendGroupFileMessageAction
    | PendingSendForwardMessageAction
)
