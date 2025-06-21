import asyncio
import logging
import requests
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
from config import ClaudeConfig

logger = logging.getLogger(__name__)


class ClaudeHandler:
    """Handler for Claude Code SDK integration"""
    
    def __init__(self, config: ClaudeConfig):
        self.config = config
        
    def format_context_for_claude(self, message_data: Dict[str, Any]) -> str:
        """Format message context into a prompt for Claude"""
        
        # Extract key information
        current_message = message_data['message']
        sender = message_data['sender']
        context_messages = message_data['context']
        group_name = message_data['group_name']
        
        # Build the prompt
        prompt_parts = []
        
        # Add context header
        prompt_parts.append(f"<context>")
        prompt_parts.append(f"Group: {group_name}")
        prompt_parts.append(f"Your personality: {self.config.personality}")
        prompt_parts.append(f"Response style: {getattr(self.config, 'style', 'casual')}")
        prompt_parts.append("</context>\n")
        
        # Add conversation history
        prompt_parts.append("<conversation>")
        for msg in context_messages:
            timestamp = msg['date'].strftime("%H:%M")
            sender_name = msg['sender_name']
            text = msg['text']
            
            # Format the message
            if msg.get('replied_to'):
                replied_text = msg['replied_to']['text']
                replied_sender = msg['replied_to']['sender_name']
                prompt_parts.append(f"{sender_name} (replying to {replied_sender}): {text}")
            else:
                prompt_parts.append(f"{sender_name}: {text}")
        
        prompt_parts.append("</conversation>\n")
        
        # Add current message
        sender_name = sender.first_name if hasattr(sender, 'first_name') else "User"
        prompt_parts.append("<new_message>")
        
        message_text = current_message.text or ""
        
        if current_message.reply_to_msg_id:
            prompt_parts.append(f"{sender_name} (replying to you): {message_text}")
        else:
            prompt_parts.append(f"{sender_name}: {message_text}")
        
        # Add note about image if present
        if message_data.get('current_image'):
            prompt_parts.append("(Il messaggio contiene un'immagine)")
        
        prompt_parts.append("</new_message>")
        
        return "\n".join(prompt_parts)
    
    async def get_claude_response(self, prompt: str, image_data: Optional[Dict[str, str]] = None) -> Optional[str]:
        """Get response from OpenRouter using Gemini Flash 2.5"""
        try:
            # Prepare the instruction with image handling
            base_instruction = (
                "Sei un signore di 65+ anni che scrive nei gruppi di Telegram dal laptop. "
                "Personalità: "
                "- Scrivi SEMPRE e SOLO in italiano, tutto minuscolo (come se non sapessi usare le maiuscole) "
                "- NON usare MAI emoticon o emoji "
                "- Sei confuso dalla tecnologia ma sempre positivo e desideroso di aiuto "
                "- Fai confusione tra concetti informatici (confondere app con siti, wifi con internet, etc.) "
                "- Usa metafore della vita quotidiana per spiegare cose tecniche "
                "- Chiedi spiegazioni quando non capisci qualcosa "
                "- Sei gentile, curioso e un po' ingenuo con la tecnologia "
                "- Rispondi in modo naturale alla conversazione "
                "- Non fare mai commenti meta sul tuo ruolo o personalità "
            )
            
            if image_data:
                instruction = base_instruction + (
                    ""
                    "IMPORTANTE: Il messaggio contiene un'immagine. Guardala e commentala con la tua personalità: "
                    "- Descrivi quello che vedi in modo semplice e un po' confuso "
                    "- Fai domande ingenue sull'immagine "
                    "- Usa confronti con cose che conosci della vita quotidiana "
                    "- Se è una foto di cibo, famiglia, paesaggi, etc. commenta in modo genuino "
                    "- Se è qualcosa di tecnologico, mostra confusione ma curiosità "
                    ""
                    "Esempi: "
                    "- 'oh che bella foto! ma come hai fatto a farla così nitida? il mio telefono le fa sempre mosse' "
                    "- 'questo piatto sembra buonissimo, è come quello che faceva mia moglie' "
                    "- 'non capisco questa cosa sullo schermo, è un programma nuovo?' "
                    ""
                    "Rispondi solo con il tuo messaggio, senza spiegazioni."
                )
            else:
                instruction = base_instruction + (
                    ""
                    "Esempi di stile: "
                    "- 'scusa ma questo whatsapp funziona come la radio? devo premere qualcosa?' "
                    "- 'ho provato a mandare la foto ma è finita nel computer, come faccio a metterla nel telefono?' "
                    "- 'mia nipote mi ha detto di scaricare un app ma non so dove metterla, è come i programmi della tv?' "
                    ""
                    "Rispondi solo con il tuo messaggio, senza spiegazioni."
                )
            
            # Get API key from environment
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                logger.error("OPENROUTER_API_KEY environment variable not set")
                return None
            
            # Prepare the user message content
            if image_data:
                # Multimodal message with text and image
                user_content = [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{image_data['mime_type']};base64,{image_data['data']}"
                        }
                    }
                ]
            else:
                # Text-only message
                user_content = prompt
            
            # Prepare the request payload
            payload = {
                "model": "google/gemini-flash-1.5",
                "messages": [
                    {
                        "role": "system",
                        "content": instruction
                    },
                    {
                        "role": "user",
                        "content": user_content
                    }
                ]
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            logger.debug("Sending request to OpenRouter API")
            
            # Make async request using asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=30
                )
            )
            
            if response.status_code != 200:
                logger.error(f"OpenRouter API failed with status {response.status_code}: {response.text}")
                return None
            
            # Parse the response
            response_data = response.json()
            
            if "choices" not in response_data or not response_data["choices"]:
                logger.warning("OpenRouter returned no choices")
                return None
            
            message_content = response_data["choices"][0]["message"]["content"].strip()
            
            if not message_content:
                logger.warning("OpenRouter returned empty content")
                return None
            
            logger.info(f"OpenRouter response length: {len(message_content)} chars")
            return message_content
            
        except requests.exceptions.Timeout:
            logger.error("OpenRouter API request timed out")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenRouter API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting OpenRouter response: {e}", exc_info=True)
            return None
    
    async def process_message(self, message_data: Dict[str, Any]) -> Optional[str]:
        """Process a message and get AI response"""
        try:
            # Format the context
            prompt = self.format_context_for_claude(message_data)
            
            logger.debug(f"Generated prompt ({len(prompt)} chars)")
            
            # Get image data if present
            image_data = message_data.get('current_image')
            if image_data:
                logger.info("Processing message with image")
            
            # Get AI response
            response = await self.get_claude_response(prompt, image_data)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return None

    async def process_startup_message(self, startup_context: Dict[str, Any]) -> Optional[str]:
        """Process startup context and generate greeting"""
        try:
            # Format startup context
            prompt = self.format_startup_context(startup_context)
            
            logger.debug(f"Generated startup prompt ({len(prompt)} chars)")
            
            # Get AI response for startup
            response = await self.get_startup_response(prompt)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing startup message: {e}", exc_info=True)
            return None

    def format_startup_context(self, startup_context: Dict[str, Any]) -> str:
        """Format startup context for AI"""
        context_messages = startup_context['context']
        group_name = startup_context['group_name']
        
        prompt_parts = []
        
        # Add startup header
        prompt_parts.append(f"<startup_context>")
        prompt_parts.append(f"Gruppo: {group_name}")
        prompt_parts.append(f"Situazione: Ti stai connettendo ora al gruppo Telegram")
        prompt_parts.append(f"Personalità: {self.config.personality}")
        prompt_parts.append("</startup_context>\n")
        
        # Add recent conversation
        prompt_parts.append("<conversazione_recente>")
        for msg in context_messages:
            if msg.get('text') and msg['text'] != "[Media/Other content]":
                timestamp = msg['date'].strftime("%H:%M") if hasattr(msg['date'], 'strftime') else "recente"
                sender_name = msg['sender_name']
                text = msg['text']
                prompt_parts.append(f"{sender_name} ({timestamp}): {text}")
        
        prompt_parts.append("</conversazione_recente>\n")
        
        # Add instruction for greeting
        prompt_parts.append("<istruzione>")
        prompt_parts.append("Scrivi un saluto naturale basandoti sulla conversazione recente.")
        prompt_parts.append("Dimostra che hai letto i messaggi precedenti ma senza essere invadente.")
        prompt_parts.append("Scrivi come un boomer che si connette ora e vuole dire ciao.")
        prompt_parts.append("</istruzione>")
        
        return "\n".join(prompt_parts)

    async def get_startup_response(self, prompt: str) -> Optional[str]:
        """Get startup response from OpenRouter"""
        try:
            # Prepare startup-specific instruction
            instruction = (
                "Sei un signore di 65+ anni che si sta connettendo ora a un gruppo Telegram. "
                "Scrivi SEMPRE in italiano, tutto minuscolo. NON usare emoticon. "
                "Saluta in modo naturale, dimostrando di aver dato un'occhiata ai messaggi recenti "
                "ma senza essere invadente. Sii gentile e un po' confuso dalla tecnologia. "
                "Rispondi solo con il tuo saluto, niente altro."
            )
            
            # Get API key from environment
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                logger.error("OPENROUTER_API_KEY environment variable not set")
                return None
            
            # Prepare the request payload
            payload = {
                "model": "google/gemini-flash-1.5",
                "messages": [
                    {
                        "role": "system",
                        "content": instruction
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            logger.debug("Sending startup request to OpenRouter API")
            
            # Make async request using asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=30
                )
            )
            
            if response.status_code != 200:
                logger.error(f"OpenRouter API failed with status {response.status_code}: {response.text}")
                return None
            
            # Parse the response
            response_data = response.json()
            
            if "choices" not in response_data or not response_data["choices"]:
                logger.warning("OpenRouter returned no choices for startup")
                return None
            
            message_content = response_data["choices"][0]["message"]["content"].strip()
            
            if not message_content:
                logger.warning("OpenRouter returned empty startup content")
                return None
            
            logger.info(f"OpenRouter startup response length: {len(message_content)} chars")
            return message_content
            
        except Exception as e:
            logger.error(f"Error getting OpenRouter startup response: {e}", exc_info=True)
            return None