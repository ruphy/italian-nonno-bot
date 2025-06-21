#!/usr/bin/env python3

import asyncio
import logging
import random
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from collections import deque

from config import load_config, validate_config
from telegram_client import TelegramBot
from claude_handler import ClaudeHandler


class RateLimiter:
    """Simple rate limiter to prevent spam"""
    
    def __init__(self, max_messages: int, window_seconds: int):
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self.message_times = deque()
    
    def can_send_message(self) -> bool:
        """Check if we can send a message based on rate limits"""
        now = datetime.now()
        
        # Remove old messages outside the window
        while self.message_times and self.message_times[0] < now - timedelta(seconds=self.window_seconds):
            self.message_times.popleft()
        
        # Check if we're within the limit
        return len(self.message_times) < self.max_messages
    
    def record_message(self):
        """Record that a message was sent"""
        self.message_times.append(datetime.now())


class TelegramClaudeBot:
    """Main application class"""
    
    def __init__(self):
        self.config = None
        self.telegram_bot = None
        self.claude_handler = None
        self.rate_limiter = None
        self.running = False
        
    async def initialize(self):
        """Initialize the bot components"""
        # Load and validate configuration
        self.config = load_config()
        validate_config(self.config)
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config.log_file),
                logging.StreamHandler()
            ]
        )
        
        logger = logging.getLogger(__name__)
        logger.info("Initializing Telegram Claude Bot")
        
        # Initialize components
        self.telegram_bot = TelegramBot(self.config.telegram)
        self.claude_handler = ClaudeHandler(self.config.claude)
        self.rate_limiter = RateLimiter(
            self.config.safety.rate_limit_messages,
            self.config.safety.rate_limit_window
        )
        
        # Set message handler
        self.telegram_bot.set_message_handler(self.handle_new_message)
        
    def calculate_address_probability(self, message_text: str) -> float:
        """Calculate probability that message is addressed to the bot"""
        if not message_text:
            return 0.0
        
        text = message_text.lower()
        probability = 0.0
        
        # Question words at the beginning increase probability
        question_starters = ["come", "cosa", "perché", "quando", "dove", "chi", "quale", "quanto"]
        if any(text.startswith(q) for q in question_starters):
            probability += 0.3
        
        # Tech-related keywords that might confuse a boomer
        tech_keywords = ["app", "wifi", "internet", "computer", "telefono", "whatsapp", "telegram", 
                        "installare", "scaricare", "aggiornamento", "password", "email", "foto", 
                        "video", "link", "browser", "google", "facebook", "instagram"]
        tech_mentions = sum(1 for keyword in tech_keywords if keyword in text)
        probability += min(tech_mentions * 0.15, 0.4)
        
        # Help-seeking phrases
        help_phrases = ["aiuto", "aiutare", "spiegare", "non capisco", "non riesco", "come faccio", 
                       "qualcuno sa", "qualcuno può", "che ne pensate", "cosa fate", "consigli"]
        if any(phrase in text for phrase in help_phrases):
            probability += 0.35
        
        # Question marks increase probability
        if "?" in text:
            probability += 0.2
        
        # Addressing the group in general
        group_address = ["ragazzi", "tutti", "qualcuno", "ciao", "salve", "buongiorno", "buonasera"]
        if any(addr in text for addr in group_address):
            probability += 0.15
        
        # Confusion expressions (perfect for boomer personality)
        confusion_words = ["confuso", "capire", "spiegazione", "non so", "boh", "mah"]
        if any(word in text for word in confusion_words):
            probability += 0.25
        
        return min(probability, 1.0)

    def should_respond_to_message(self, message_data: Dict[str, Any]) -> bool:
        """Determine if the bot should respond to this message"""
        logger = logging.getLogger(__name__)
        message = message_data['message']
        message_text = message.text.lower() if message.text else ""
        
        # Always respond to direct replies
        if message.reply_to_msg_id:
            logger.info("Responding to direct reply")
            return True
        
        # Always respond to mentions (@ruphy or "riccardo")
        if "@ruphy" in message_text or "riccardo" in message_text:
            logger.info("Responding to mention")
            return True
        
        # Always respond to images (boomers love commenting on photos!)
        if message_data.get('current_image'):
            logger.info("Responding to image message")
            return True
        
        # Calculate probability that message is addressed to bot
        address_probability = self.calculate_address_probability(message_text)
        if address_probability > 0.4:  # High probability threshold
            logger.info(f"Responding to likely addressed message (probability: {address_probability:.2f})")
            return True
        elif address_probability > 0.2:  # Medium probability with random chance
            if random.random() < address_probability:
                logger.info(f"Responding to possibly addressed message (probability: {address_probability:.2f})")
                return True
        
        # Sometimes respond to regular messages (reduced to 5% since we have smarter detection)
        if random.random() < 0.05:
            logger.info("Randomly responding to regular message")
            return True
        
        logger.debug(f"Not responding to message (address probability: {address_probability:.2f})")
        return False

    def calculate_boomer_typing_time(self, message: str) -> float:
        """Calculate realistic typing time for a boomer character"""
        if not message:
            return 1.0
        
        # Boomer typing characteristics:
        # - Slower typing speed (20-30 WPM vs average 40 WPM)
        # - Pauses to think about what to type
        # - Sometimes needs to look at keyboard
        # - Might make mistakes and retype
        
        # Base typing speed: ~25 WPM = 125 characters per minute = ~2.1 chars/second
        base_chars_per_second = 4.0
        
        # Count characters (spaces count as typing time too)
        char_count = len(message)
        
        # Basic typing time
        typing_time = char_count / base_chars_per_second
        
        # Add thinking pauses (more for longer messages)
        thinking_pauses = min(char_count // 20, 5) * random.uniform(1.0, 3.0)
        
        # Add confusion factor for tech-related words
        tech_words = ['app', 'wifi', 'internet', 'computer', 'telefono', 'whatsapp', 
                     'telegram', 'password', 'email', 'foto', 'video', 'link']
        tech_mentions = sum(1 for word in tech_words if word in message.lower())
        confusion_time = tech_mentions * random.uniform(2.0, 5.0)
        
        # Add time for punctuation (boomers are careful with punctuation)
        punctuation_count = sum(1 for char in message if char in '.,!?;:')
        punctuation_time = punctuation_count * random.uniform(0.5, 1.5)
        
        # Random typing mistakes and corrections (10% chance per message)
        mistake_time = 0.0
        if random.random() < 0.1:
            mistake_time = random.uniform(3.0, 8.0)
        
        # Minimum time (always show typing for at least 2 seconds)
        total_time = max(2.0, typing_time + thinking_pauses + confusion_time + punctuation_time + mistake_time)
        
        # Maximum time (don't type for more than 60 seconds)
        total_time = min(180.0, total_time)
        
        return total_time

    async def generate_startup_greeting(self) -> Optional[str]:
        """Generate a greeting message based on recent chat context"""
        logger = logging.getLogger(__name__)
        
        try:
            # Get recent messages for context
            recent_messages = await self.telegram_bot.get_startup_context(50)
            
            if not recent_messages:
                logger.info("No recent messages found for startup context")
                return None
            
            # Create context data for the AI
            startup_context = {
                'message': type('obj', (object,), {
                    'text': '[BOT STARTUP - Generate a natural greeting based on recent conversation]',
                    'reply_to_msg_id': None
                })(),
                'sender': type('obj', (object,), {
                    'first_name': 'Sistema'
                })(),
                'context': recent_messages[-20:],  # Last 20 messages for context
                'group_name': self.telegram_bot.selected_group['name']
            }
            
            # Get AI response for startup greeting
            logger.info("Generating startup greeting based on recent chat context")
            greeting = await self.claude_handler.process_startup_message(startup_context)
            
            return greeting
            
        except Exception as e:
            logger.error(f"Error generating startup greeting: {e}", exc_info=True)
            return None

    async def handle_new_message(self, message_data: Dict[str, Any]):
        """Handle incoming messages"""
        logger = logging.getLogger(__name__)
        
        try:
            # Skip if it's a bot message and we're configured to ignore bots
            sender = message_data['sender']
            if self.config.safety.ignore_bots and hasattr(sender, 'bot') and sender.bot:
                logger.debug("Skipping bot message")
                return
            
            # Check if we should respond to this message
            if not self.should_respond_to_message(message_data):
                return
            
            # Check rate limits (but allow direct replies and mentions even if rate limited)
            message = message_data['message']
            message_text = message.text.lower() if message.text else ""
            is_direct = message.reply_to_msg_id or "@ruphy" in message_text or "riccardo" in message_text
            
            if not is_direct and not self.rate_limiter.can_send_message():
                logger.warning("Rate limit exceeded, skipping non-direct message")
                return
            
            # Add random delay for natural feel (thinking time)
            thinking_delay = random.uniform(
                self.config.response.delay_min,
                self.config.response.delay_max
            )
            logger.info(f"Thinking for {thinking_delay:.1f}s before responding")
            await asyncio.sleep(thinking_delay)
            
            # Get AI response with typing indicator
            logger.info("Getting response from AI")
            
            async def process_ai_response():
                return await self.claude_handler.process_message(message_data)
            
            # Show typing while AI processes the message
            response = await self.telegram_bot.type_while_processing(
                process_ai_response(),
                typing_interval=4.0
            )
            
            if response:
                # Calculate realistic typing time for the response
                typing_time = self.calculate_boomer_typing_time(response)
                logger.info(f"Will type for {typing_time:.1f}s to simulate boomer typing speed")
                
                # Show typing indicator for calculated time
                await self.telegram_bot.start_typing()
                await asyncio.sleep(typing_time)
                
                # Send the response
                await self.telegram_bot.send_message(
                    response,
                    reply_to=message_data['message'].id
                )
                
                # Record the message for rate limiting
                self.rate_limiter.record_message()
                logger.info("Response sent successfully")
            else:
                logger.warning("No response from AI")
                
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
    
    async def select_group_interactive(self):
        """Interactive group selection"""
        logger = logging.getLogger(__name__)
        
        # Display available groups
        groups = await self.telegram_bot.display_groups()
        
        if not groups:
            print("No groups found. Make sure you're a member of at least one group.")
            return False
        
        # Get user selection
        while True:
            try:
                selection = input("\nEnter the number of the group to monitor (or 'q' to quit): ")
                
                if selection.lower() == 'q':
                    return False
                
                group_index = int(selection) - 1
                
                if await self.telegram_bot.select_group(group_index, groups):
                    print(f"\n✓ Selected: {groups[group_index]['name']}")
                    return True
                else:
                    print("Invalid selection. Please try again.")
                    
            except ValueError:
                print("Please enter a valid number or 'q' to quit.")
            except KeyboardInterrupt:
                return False
    
    async def run(self):
        """Main bot loop"""
        logger = logging.getLogger(__name__)
        
        try:
            # Initialize components
            await self.initialize()
            
            # Start Telegram client
            print("Connecting to Telegram...")
            await self.telegram_bot.start()
            print("✓ Connected to Telegram")
            
            # Select group
            if not await self.select_group_interactive():
                print("No group selected. Exiting.")
                return
            
            # Start monitoring
            await self.telegram_bot.start_monitoring()
            
            print(f"\n✓ Bot is now active!")
            print(f"Monitoring group: {self.telegram_bot.selected_group['name']}")
            print(f"Personality: {self.config.claude.personality[:50]}...")
            print(f"Rate limit: {self.config.safety.rate_limit_messages} messages per {self.config.safety.rate_limit_window}s")
            
            # Generate and send startup greeting
            print("\nGenerating startup greeting based on recent messages...")
            startup_greeting = await self.generate_startup_greeting()
            
            if startup_greeting:
                print(f"Sending startup greeting: {startup_greeting[:60]}...")
                
                # Calculate typing time for startup greeting
                typing_time = self.calculate_boomer_typing_time(startup_greeting)
                print(f"Typing for {typing_time:.1f}s to simulate realistic greeting...")
                
                # Show typing indicator then send message
                await self.telegram_bot.start_typing()
                await asyncio.sleep(typing_time)
                await self.telegram_bot.send_message(startup_greeting)
                
                print("✓ Startup greeting sent!")
            else:
                print("No startup greeting generated")
            
            print("\nPress Ctrl+C to stop the bot.\n")
            
            self.running = True
            
            # Keep the bot running
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
        finally:
            # Cleanup
            if self.telegram_bot:
                await self.telegram_bot.disconnect()
            logger.info("Bot stopped")
    
    def stop(self):
        """Stop the bot"""
        self.running = False


async def main():
    """Main entry point"""
    bot = TelegramClaudeBot()
    
    # Setup signal handlers
    def signal_handler(sig, frame):
        print("\nShutting down...")
        bot.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the bot
    await bot.run()


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
