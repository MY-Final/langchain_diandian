"""文件/转发 action 执行器。"""

from __future__ import annotations

from chat_app.skills.file_send import (
    PendingSendGroupFileMessageAction,
    PendingSendPrivateFileAction,
)
from chat_app.skills.forward_message import PendingSendForwardMessageAction
from chat_app.skills.group_file import (
    PendingDeleteGroupFileAction,
    PendingGetGroupFilesAction,
    PendingUploadGroupFileAction,
)
from onebot_gateway.app.action_executors.base import (
    ActionExecutor,
    ActionResult,
    ChatMessageSender,
)
from onebot_gateway.app.action_executors.permissioned import PermissionedActionExecutor


class UploadGroupFileActionExecutor(
    PermissionedActionExecutor[PendingUploadGroupFileAction]
):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingUploadGroupFileAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        denied = self._check_permission(event, "upload_group_file")
        if denied is not None:
            return denied
        await sender.upload_group_file(
            action.group_id, action.file, action.name, folder=action.folder
        )
        return ActionResult(
            action="upload_group_file",
            success=True,
            message=f"已上传群文件 {action.name}。",
        )


class GetGroupFilesActionExecutor(ActionExecutor[PendingGetGroupFilesAction]):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingGetGroupFilesAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        result = await sender.get_group_files(
            action.group_id, folder_id=action.folder_id
        )
        return ActionResult(
            action="get_group_files",
            success=True,
            message=f"已获取群文件列表：{result}",
        )


class DeleteGroupFileActionExecutor(
    PermissionedActionExecutor[PendingDeleteGroupFileAction]
):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingDeleteGroupFileAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        denied = self._check_permission(event, "delete_group_file")
        if denied is not None:
            return denied
        await sender.delete_group_file(action.group_id, action.file_id)
        return ActionResult(
            action="delete_group_file",
            success=True,
            message=f"已删除群文件 {action.file_id}。",
        )


class SendPrivateFileActionExecutor(
    PermissionedActionExecutor[PendingSendPrivateFileAction]
):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingSendPrivateFileAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        denied = self._check_permission(event, "send_private_file")
        if denied is not None:
            return denied
        await sender.upload_private_file(action.user_id, action.file)
        return ActionResult(
            action="send_private_file",
            success=True,
            message=f"已发送私聊文件给用户 {action.user_id}。",
        )


class SendGroupFileMessageActionExecutor(
    PermissionedActionExecutor[PendingSendGroupFileMessageAction]
):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingSendGroupFileMessageAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        denied = self._check_permission(event, "send_group_file_message")
        if denied is not None:
            return denied
        file_name = (
            action.name if action.name else action.file.split("/")[-1].split("\\")[-1]
        )
        await sender.upload_group_file(action.group_id, action.file, file_name)
        return ActionResult(
            action="send_group_file_message",
            success=True,
            message=f"已上传群文件 {file_name}。",
        )


class SendForwardMessageActionExecutor(
    PermissionedActionExecutor[PendingSendForwardMessageAction]
):
    async def execute(
        self,
        sender: ChatMessageSender,
        action: PendingSendForwardMessageAction,
        *,
        bot_user_id: int | None = None,
        event=None,
    ) -> ActionResult:
        denied = self._check_permission(event, "send_forward_message")
        if denied is not None:
            return denied
        messages = [node.to_dict() for node in action.nodes]
        if action.is_group:
            await sender.send_group_forward_message(action.target_id, messages)
        else:
            await sender.send_private_forward_message(action.target_id, messages)
        return ActionResult(
            action="send_forward_message",
            success=True,
            message=f"已发送合并转发消息到 {'群聊' if action.is_group else '私聊'} {action.target_id}。",
        )
