from telethon import TelegramClient, events
from telethon.tl.types import MessageService, MessageActionChatDeleteUser
from ..core.config import get_settings
from .. import database
from ..events import file_update_queue
import asyncio
import json

class TelegramListener:
    def __init__(self):
        settings = get_settings()
        self.client = TelegramClient(
            'bot_session',
            settings.API_ID,
            settings.API_HASH
        )
        self.channel_name = settings.CHANNEL_NAME
        
    async def start(self):
        """启动 Telethon 客户端并注册事件处理器"""
        await self.client.start(bot_token=get_settings().BOT_TOKEN)
        print(f"Telethon 监听器已启动，正在监听频道: {self.channel_name}")
        
        @self.client.on(events.MessageDeleted)
        async def handle_deleted(event):
            """处理消息删除事件"""
            if not hasattr(event, 'deleted_ids'):
                return

            for deleted_id in event.deleted_ids:
                print(f"检测到消息删除: {deleted_id}")

                # 从数据库中查找并删除
                deleted_file_id = database.delete_file_by_message_id(deleted_id)

                if deleted_file_id:
                    print(f"已从数据库删除文件: {deleted_file_id}")

                    # 通知前端
                    await file_update_queue.put(json.dumps({
                        "action": "delete",
                        "file_id": deleted_file_id
                    }))

        @self.client.on(events.MessageEdited)
        async def handle_edited(event):
            """处理消息编辑事件（caption 变化）"""
            message = event.message
            if not message or not message.document:
                return

            message_id = message.id
            new_caption = message.text or ""

            print(f"检测到消息编辑: {message_id}, 新 caption: {new_caption}")

            # 更新数据库中的 description
            updated_file_id = database.update_description_by_message_id(message_id, new_caption)

            if updated_file_id:
                print(f"已更新文件描述: {updated_file_id}")

                # 通知前端
                await file_update_queue.put(json.dumps({
                    "action": "update_description",
                    "file_id": updated_file_id,
                    "description": new_caption
                }))

        await self.client.run_until_disconnected()
    
    async def stop(self):
        """停止客户端"""
        await self.client.disconnect()

# 全局实例
_listener_instance = None

def get_listener() -> TelegramListener:
    global _listener_instance
    if _listener_instance is None:
        _listener_instance = TelegramListener()
    return _listener_instance
