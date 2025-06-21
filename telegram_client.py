import asyncio
import logging
import base64
import mimetypes
import io
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from telethon import TelegramClient, events, functions, types
from telethon.tl.types import Dialog, Channel, Chat, User, Message
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.errors import SessionPasswordNeededError
from config import TelegramConfig

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram client for monitoring and responding to messages"""
    
    def __init__(self, config: TelegramConfig):
        self.config = config
        self.client = TelegramClient(
            config.session_name,
            config.api_id,
            config.api_hash
        )
        self.selected_group: Optional[Dialog] = None
        self.message_handler = None
        
    async def start(self):
        """Start the Telegram client and authenticate"""
        try:
            await self.client.start(phone=self.config.phone_number)
            logger.info("Telegram client started successfully")
        except EOFError:
            logger.error("Authentication required. Please run the bot interactively first to authenticate.")
            logger.error("Run: python main.py")
            raise RuntimeError("First-time authentication required. Please run interactively.")
        
    async def get_groups(self) -> List[Dict[str, Any]]:
        """Get all groups/channels sorted by last message time"""
        dialogs = []
        # Calculate 48 hours ago
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=48)
        
        async for dialog in self.client.iter_dialogs():
            # Only include groups and channels
            if isinstance(dialog.entity, (Channel, Chat)):
                # Skip if it's a broadcast channel (not a group)
                if hasattr(dialog.entity, 'broadcast') and dialog.entity.broadcast:
                    continue
                
                # Skip if no message or message is older than 48 hours
                if not dialog.message or not dialog.message.date:
                    continue
                    
                if dialog.message.date < cutoff_time:
                    continue
                
                dialogs.append({
                    'id': dialog.id,
                    'name': dialog.name,
                    'entity': dialog.entity,
                    'dialog': dialog,
                    'unread_count': dialog.unread_count,
                    'last_message_date': dialog.message.date,
                    'participants_count': getattr(dialog.entity, 'participants_count', 'Unknown')
                })
        
        # Sort by last message date (most recent first)
        dialogs.sort(
            key=lambda x: x['last_message_date'],
            reverse=True
        )
        
        return dialogs
    
    async def display_groups(self) -> List[Dict[str, Any]]:
        """Display available groups and return the list"""
        groups = await self.get_groups()
        
        if not groups:
            logger.warning("No groups found with activity in the last 48 hours")
            return []
        
        print("\n=== Available Groups (active in last 48 hours) ===\n")
        now = datetime.now(timezone.utc)
        
        for i, group in enumerate(groups, 1):
            # Calculate time ago
            time_diff = now - group['last_message_date']
            hours_ago = int(time_diff.total_seconds() / 3600)
            minutes_ago = int((time_diff.total_seconds() % 3600) / 60)
            
            if hours_ago > 0:
                time_ago = f"{hours_ago}h {minutes_ago}m ago"
            else:
                time_ago = f"{minutes_ago}m ago"
            
            print(f"{i}. {group['name']}")
            print(f"   Members: {group['participants_count']}")
            print(f"   Last message: {time_ago}")
            print(f"   Unread: {group['unread_count']}")
            print()
        
        return groups
    
    async def select_group(self, group_index: int, groups: List[Dict[str, Any]]) -> bool:
        """Select a group to monitor"""
        if 0 <= group_index < len(groups):
            self.selected_group = groups[group_index]
            logger.info(f"Selected group: {self.selected_group['name']}")
            return True
        else:
            logger.error("Invalid group selection")
            return False
    
    async def get_message_context(self, event_message: Message, limit: int = 20) -> List[Dict[str, Any]]:
        """Get message context including previous messages and replies"""
        messages = []
        
        # Get recent messages from the chat
        async for message in self.client.iter_messages(
            self.selected_group['entity'],
            limit=limit
        ):
            sender = await message.get_sender()
            sender_name = "Unknown"
            
            if isinstance(sender, User):
                sender_name = sender.first_name or sender.username or f"User {sender.id}"
            elif isinstance(sender, (Channel, Chat)):
                sender_name = sender.title
            
            msg_data = {
                'id': message.id,
                'text': message.text or "[Media/Other content]",
                'sender_id': message.sender_id,
                'sender_name': sender_name,
                'date': message.date,
                'reply_to_msg_id': message.reply_to_msg_id,
                'is_bot': getattr(sender, 'bot', False) if isinstance(sender, User) else False,
                'image': None  # Will be populated if message has photo
            }
            
            # Download and encode image if present
            if message.photo:
                image_data = await self.download_and_encode_image(message)
                if image_data:
                    msg_data['image'] = image_data
                    msg_data['text'] = message.text or "[Foto]"  # Italian for "Photo"
            
            # If this message is a reply, try to get the original message
            if message.reply_to_msg_id:
                try:
                    replied_msg = await self.client.get_messages(
                        self.selected_group['entity'],
                        ids=message.reply_to_msg_id
                    )
                    if replied_msg:
                        replied_sender = await replied_msg.get_sender()
                        replied_sender_name = "Unknown"
                        if isinstance(replied_sender, User):
                            replied_sender_name = replied_sender.first_name or replied_sender.username
                        
                        msg_data['replied_to'] = {
                            'text': replied_msg.text or "[Media/Other content]",
                            'sender_name': replied_sender_name
                        }
                except Exception as e:
                    logger.warning(f"Could not fetch replied message: {e}")
            
            messages.append(msg_data)
        
        # Reverse to get chronological order
        messages.reverse()
        
        return messages
    
    async def get_startup_context(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent messages for startup context"""
        if not self.selected_group:
            return []
        
        # Use the existing get_message_context method but with a dummy message
        dummy_message = type('obj', (object,), {
            'id': 0,
            'text': '',
            'sender_id': 0,
            'date': datetime.now(timezone.utc),
            'reply_to_msg_id': None
        })()
        
        return await self.get_message_context(dummy_message, limit=limit)

    async def download_and_encode_image(self, message: Message) -> Optional[Dict[str, str]]:
        """Download image from message and encode as base64"""
        try:
            if not message.photo:
                return None
            
            # Download the image to memory
            image_bytes = await self.client.download_media(message.photo, file=bytes)
            
            if not image_bytes:
                logger.warning("Failed to download image bytes")
                return None
            
            # Encode to base64
            encoded_image = base64.b64encode(image_bytes).decode('utf-8')
            
            # Determine MIME type (default to JPEG for Telegram photos)
            mime_type = "image/jpeg"
            
            return {
                'data': encoded_image,
                'mime_type': mime_type
            }
            
        except Exception as e:
            logger.error(f"Error downloading/encoding image: {e}")
            return None

    def set_message_handler(self, handler):
        """Set the message handler callback"""
        self.message_handler = handler
    
    async def start_monitoring(self):
        """Start monitoring the selected group for new messages"""
        if not self.selected_group:
            raise ValueError("No group selected")
        
        @self.client.on(events.NewMessage(chats=self.selected_group['entity']))
        async def handle_new_message(event):
            try:
                # Get sender information
                sender = await event.get_sender()
                
                # Skip if sender is a bot (based on config)
                if isinstance(sender, User) and sender.bot:
                    logger.debug(f"Skipping message from bot: {sender.username}")
                    return
                
                # Get message context
                context = await self.get_message_context(event.message)
                
                # Download image if present in the new message
                current_message_image = None
                if event.message.photo:
                    current_message_image = await self.download_and_encode_image(event.message)
                
                # Prepare message data
                message_data = {
                    'message': event.message,
                    'sender': sender,
                    'context': context,
                    'group_name': self.selected_group['name'],
                    'current_image': current_message_image
                }
                
                # Call the message handler if set
                if self.message_handler:
                    await self.message_handler(message_data)
                    
            except Exception as e:
                logger.error(f"Error handling new message: {e}", exc_info=True)
        
        logger.info(f"Started monitoring group: {self.selected_group['name']}")
        
    async def start_typing(self):
        """Start showing typing indicator"""
        if not self.selected_group:
            return
        
        try:
            await self.client(functions.messages.SetTypingRequest(
                peer=self.selected_group['entity'],
                action=types.SendMessageTypingAction()
            ))
        except Exception as e:
            logger.warning(f"Failed to start typing indicator: {e}")

    async def stop_typing(self):
        """Stop showing typing indicator"""
        if not self.selected_group:
            return
        
        try:
            await self.client(functions.messages.SetTypingRequest(
                peer=self.selected_group['entity'],
                action=types.SendMessageCancelAction()
            ))
        except Exception as e:
            logger.warning(f"Failed to stop typing indicator: {e}")

    async def type_while_processing(self, processing_task, typing_interval: float = 4.0):
        """Show typing indicator while processing a task"""
        if not self.selected_group:
            return await processing_task
        
        typing_active = True
        
        async def keep_typing():
            while typing_active:
                try:
                    await self.client(functions.messages.SetTypingRequest(
                        peer=self.selected_group['entity'],
                        action=types.SendMessageTypingAction()
                    ))
                    await asyncio.sleep(typing_interval)
                except Exception as e:
                    logger.warning(f"Typing indicator error: {e}")
                    break
        
        # Start typing task
        typing_task = asyncio.create_task(keep_typing())
        
        try:
            # Wait for the processing to complete
            result = await processing_task
            return result
        finally:
            # Stop typing
            typing_active = False
            typing_task.cancel()
            try:
                await typing_task
            except asyncio.CancelledError:
                pass
            await self.stop_typing()

    async def send_message(self, text: str, reply_to: Optional[int] = None):
        """Send a message to the selected group"""
        if not self.selected_group:
            raise ValueError("No group selected")
        
        await self.client.send_message(
            self.selected_group['entity'],
            text,
            reply_to=reply_to
        )
        logger.info(f"Sent message to {self.selected_group['name']}")
    
    async def disconnect(self):
        """Disconnect from Telegram"""
        await self.client.disconnect()
        logger.info("Disconnected from Telegram")