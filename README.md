# Italian Nonno Bot 🇮🇹👴

A fun Telegram bot that impersonates a lovable Italian grandfather (nonno) in your friend group chats! This bot uses advanced AI to create realistic, endearing responses with authentic boomer characteristics like slower typing, tech confusion, and heartwarming Italian personality.

## 🎭 Features

- **Authentic Italian Grandfather Personality**: Warm, caring, sometimes confused by technology
- **Realistic Human Simulation**: 
  - Slower typing speed (~25 WPM vs average 40 WPM)
  - Thinking pauses and tech-related confusion delays
  - Occasional "typing mistakes" with correction time
- **Intelligent Response Detection**: 
  - Responds to direct replies, mentions, and images
  - Smart probability-based detection for tech questions and help requests
  - Reduced random responses thanks to intelligent targeting
- **Multimodal Capabilities**: Comments on photos with Italian boomer charm
- **Advanced Safety Features**: Rate limiting, context awareness, and responsible AI usage
- **Natural Conversation Flow**: Maintains chat history and responds contextually

## 📋 Prerequisites

- Python 3.8+
- Telegram account (you'll use your personal account, not a bot token)
- OpenRouter API key (for accessing AI models like Gemini Flash 1.5)
- Basic familiarity with Python and command line

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/ruphy/italian-nonno-bot.git
   cd italian-nonno-bot
   ```

2. **Set up Python environment**
   ```bash
   # Create virtual environment (recommended)
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Get Telegram API credentials**
   - Visit [https://my.telegram.org](https://my.telegram.org)
   - Log in with your phone number
   - Click "API development tools"
   - Create a new application (choose any name/description)
   - Copy your `api_id` and `api_hash`

4. **Get OpenRouter API key**
   - Visit [https://openrouter.ai/keys](https://openrouter.ai/keys)
   - Create an account or log in
   - Generate an API key
   - Add some credits to your account (Gemini 2.0 Flash is very affordable)

5. **Configure the bot**
   ```bash
   # Copy the example configuration
   cp .env.example .env
   
   # Edit .env with your favorite text editor
   nano .env  # or vim, code, etc.
   ```
   
   Fill in your credentials:
   - `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` from step 3
   - `TELEGRAM_PHONE_NUMBER` (your phone number with country code)
   - `OPENROUTER_API_KEY` from step 4
   - Customize `BOT_PERSONALITY` to match your desired character

6. **First-time authentication (optional but recommended)**
   ```bash
   # Optional: Authenticate separately for cleaner setup
   python auth.py
   ```
   
   Or authenticate during first run:
   ```bash
   python main.py
   ```
   
   On first run, you'll need to:
   - Enter the verification code sent to your phone
   - Select which Telegram group to monitor
   - Watch as your Italian nonno comes to life! 🎉

## ⚙️ Configuration

The bot is highly customizable through the `.env` file:

### Personality Settings
- `BOT_PERSONALITY`: Define your character's personality (Italian grandfather by default)
- `AI_MODEL`: OpenRouter model to use (default: `google/gemini-2.0-flash-exp`)

### Behavior Settings  
- `CONTEXT_MESSAGES`: Number of previous messages to remember (default: 20)
- `RESPONSE_DELAY_MIN/MAX`: Thinking time before responding (1-3 seconds)
- `RATE_LIMIT_MESSAGES`: Maximum messages per minute (default: 10)

### Safety Settings
- `IGNORE_BOTS`: Whether to ignore other bots (recommended: `true`)

## 🎮 Usage

1. **Start the bot**: `python main.py`
2. **First-time setup**: Enter phone verification code
3. **Group selection**: Choose from your available groups (sorted by activity)
4. **Enjoy**: Watch your Italian nonno charm the group! 

**To stop**: Press `Ctrl+C`

## 🔐 Security & Privacy

**⚠️ Important Security Notes:**
- Your Telegram session is stored locally in `.session` files
- **Never commit your `.env` file** - it contains your credentials
- The bot uses your personal Telegram account (be mindful of ToS)
- Rate limiting prevents spam detection
- All data stays local - no external servers involved

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| "No groups found" | Make sure you're in at least one group/supergroup |
| Authentication fails | Delete `.session` files and restart |
| AI not responding | Check your OpenRouter API key and credits |
| Rate limit errors | Adjust `RATE_LIMIT_MESSAGES` in `.env` |
| Bot seems too active | Increase delay times or reduce response probability |

## 🏗️ Architecture

- **`main.py`**: Core bot logic and message handling
- **`telegram_client.py`**: Telegram MTProto integration  
- **`claude_handler.py`**: AI model interaction via OpenRouter
- **`config.py`**: Configuration management
- **`auth.py`**: Authentication helpers

## 🤝 Contributing

This is a fun personal project, but contributions are welcome! Feel free to:
- Report bugs
- Suggest personality improvements  
- Add new language support
- Enhance the typing simulation

## 📄 License

MIT License - Feel free to use this for your own friend groups! Just remember to use it responsibly and in accordance with Telegram's Terms of Service.

## 🙏 Acknowledgments

- Built with [Telethon](https://github.com/LonamiWebs/Telethon) for Telegram integration
- AI powered by [OpenRouter](https://openrouter.ai/) and Google's Gemini models
- Inspired by all the lovable Italian grandparents who struggle with technology ❤️