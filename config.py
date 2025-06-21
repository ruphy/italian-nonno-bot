import os
from dataclasses import dataclass
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
load_dotenv()


@dataclass
class TelegramConfig:
    """Telegram API configuration"""
    api_id: int
    api_hash: str
    phone_number: str
    session_name: str = "telegram_claude_bot"


@dataclass
class ClaudeConfig:
    """Claude API configuration"""
    api_key: str
    model: str
    max_turns: int
    personality: str


@dataclass
class ResponseConfig:
    """Response behavior configuration"""
    context_messages: int
    delay_min: float
    delay_max: float
    trigger_words: list


@dataclass
class SafetyConfig:
    """Safety and rate limiting configuration"""
    rate_limit_messages: int
    rate_limit_window: int
    ignore_bots: bool


@dataclass
class AppConfig:
    """Main application configuration"""
    telegram: TelegramConfig
    claude: ClaudeConfig
    response: ResponseConfig
    safety: SafetyConfig
    log_level: str
    log_file: str


def load_config() -> AppConfig:
    """Load configuration from environment variables"""
    
    # Validate required environment variables
    required_vars = [
        "TELEGRAM_API_ID",
        "TELEGRAM_API_HASH",
        "TELEGRAM_PHONE_NUMBER"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Create configuration objects
    telegram_config = TelegramConfig(
        api_id=int(os.getenv("TELEGRAM_API_ID")),
        api_hash=os.getenv("TELEGRAM_API_HASH"),
        phone_number=os.getenv("TELEGRAM_PHONE_NUMBER")
    )
    
    claude_config = ClaudeConfig(
        api_key="",  # Not needed when using OpenRouter API directly
        model=os.getenv("AI_MODEL", "google/gemini-2.0-flash-exp"),
        max_turns=int(os.getenv("AI_MAX_TURNS", "1")),
        personality=os.getenv(
            "BOT_PERSONALITY",
            "You are a helpful and friendly assistant participating in a Telegram group chat."
        )
    )
    
    # Parse trigger words from comma-separated string
    trigger_words_str = os.getenv("TRIGGER_WORDS", "")
    trigger_words = [word.strip().lower() for word in trigger_words_str.split(",") if word.strip()]
    
    response_config = ResponseConfig(
        context_messages=int(os.getenv("CONTEXT_MESSAGES", "20")),
        delay_min=float(os.getenv("RESPONSE_DELAY_MIN", "1")),
        delay_max=float(os.getenv("RESPONSE_DELAY_MAX", "3")),
        trigger_words=trigger_words
    )
    
    safety_config = SafetyConfig(
        rate_limit_messages=int(os.getenv("RATE_LIMIT_MESSAGES", "10")),
        rate_limit_window=int(os.getenv("RATE_LIMIT_WINDOW", "60")),
        ignore_bots=os.getenv("IGNORE_BOTS", "true").lower() == "true"
    )
    
    return AppConfig(
        telegram=telegram_config,
        claude=claude_config,
        response=response_config,
        safety=safety_config,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=os.getenv("LOG_FILE", "telegram_bot.log")
    )


def validate_config(config: AppConfig) -> None:
    """Validate configuration values"""
    
    # Validate log level
    valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
    if config.log_level not in valid_log_levels:
        raise ValueError(f"Invalid log level. Must be one of: {', '.join(valid_log_levels)}")
    
    # Validate numeric ranges
    if config.response.context_messages < 1:
        raise ValueError("Context messages must be at least 1")
    
    if config.response.delay_min < 0 or config.response.delay_max < config.response.delay_min:
        raise ValueError("Invalid response delay configuration")
    
    if config.safety.rate_limit_messages < 1 or config.safety.rate_limit_window < 1:
        raise ValueError("Invalid rate limit configuration")