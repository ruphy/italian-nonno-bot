# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Bot
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the bot
python main.py
```

### Testing Components
```bash
# Test individual components (examples from recent development)
python -c "from main import TelegramClaudeBot; bot = TelegramClaudeBot(); print(bot.calculate_boomer_typing_time('test message'))"

# Test configuration loading
python -c "from config import load_config; config = load_config(); print('Config loaded successfully')"

# Test OpenRouter API structure (without API key)
python -c "from claude_handler import ClaudeHandler; from config import ClaudeConfig; print('Components importable')"
```

## Architecture Overview

### Core Components
This is a Telegram bot that impersonates an Italian boomer user with multimodal capabilities. The architecture follows a layered pattern:

**Main Application Layer (`main.py`)**
- `TelegramClaudeBot`: Main orchestrator class that coordinates all components
- `RateLimiter`: Sliding window rate limiter to prevent spam
- Message flow: handles response logic, typing simulation, and startup greeting

**Telegram Integration (`telegram_client.py`)**
- `TelegramBot`: Manages Telegram MTProto connection using Telethon
- Group selection with activity-based sorting (48-hour window)
- Image download and base64 encoding for multimodal messages
- Realistic typing indicators using `SetTypingRequest` API

**AI Processing (`claude_handler.py`)**
- `ClaudeHandler`: Interfaces with OpenRouter API using Gemini Flash 1.5
- Context formatting for conversation history and multimodal content
- Separate methods for regular messages vs startup greetings
- Italian boomer personality injection with image understanding

**Configuration (`config.py`)**
- Dataclass-based configuration with environment variable loading
- Separate configs for Telegram, AI model, response behavior, and safety

### Key Architectural Patterns

**Message Response Flow**
1. Message detection with intelligent probability scoring
2. Thinking delay (configurable random range)
3. Typing indicator during AI processing
4. Calculated typing time based on boomer characteristics
5. Final message delivery

**Multimodal Processing**
- Images are automatically downloaded from Telegram messages
- Base64 encoding for OpenRouter API compatibility
- Enhanced personality prompts for image understanding
- Italian boomer reactions to photos with tech confusion

**Intelligent Response Logic**
- Always responds to: direct replies, @mentions, name mentions, images
- Smart detection using probability scoring for tech questions, help requests, confusion expressions
- Reduced random responses (5%) due to intelligent targeting

**Boomer Personality Simulation**
- Realistic typing speeds (~25 WPM vs average 40 WPM)
- Tech confusion delays for words like 'wifi', 'app', 'computer'
- Thinking pauses and punctuation care
- 10% chance of typing mistakes with correction time

## Environment Configuration

The bot requires these environment variables in `.env`:
- `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_PHONE_NUMBER`: Telegram MTProto credentials
- `OPENROUTER_API_KEY`: For Gemini Flash 1.5 multimodal model
- `BOT_PERSONALITY`: Italian boomer character description
- `AI_MODEL`: OpenRouter model name (defaults to google/gemini-flash-1.5)
- Response timing, rate limiting, and safety configurations

## Session Management

- Telegram sessions are persisted in `.session` files
- First run requires phone authentication
- Subsequent runs auto-authenticate with stored session
- Bot operates using user's personal Telegram account (not bot API)

## Key Implementation Details

**Message Context**: Bot maintains conversation history (default 20 messages) and formats it for AI processing with timestamps and reply chains.

**Startup Behavior**: Bot reads last 50 messages from selected group and generates contextual Italian greeting.

**Rate Limiting**: Direct replies and mentions bypass rate limits; only random responses are rate-limited.

**Error Handling**: Graceful fallbacks for image download failures, API timeouts, and typing indicator errors.

**Typing Simulation**: Two-phase typing - first during AI processing, then calculated realistic typing time based on message characteristics.