import httpx
from typing import Optional, AsyncGenerator
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import ProviderError

class SpeechService:
    def __init__(self):
        self.api_key = settings.DEEPGRAM_API_KEY
        self.is_configured = bool(self.api_key)

    async def synthesize_speech(self, text: str, voice: str = "aura-asteria-en") -> bytes:
        """Synthesizes text into MP3/linear16 audio bytes using Deepgram Aura."""
        if not self.is_configured:
            # Fallback mock speech output
            logger.info("Deepgram not configured; returning synthetic audio placeholder")
            return b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00"

        url = f"https://api.deepgram.com/v1/speak?model={voice}"
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {"text": text}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    return resp.content
                else:
                    logger.error("Deepgram TTS error", status=resp.status_code, body=resp.text)
                    raise ProviderError("Deepgram", f"TTS failed with status {resp.status_code}")
        except Exception as e:
            logger.error("Deepgram TTS network failure", error=str(e))
            raise ProviderError("Deepgram", str(e))

    async def transcribe_audio(self, audio_bytes: bytes, mimetype: str = "audio/wav") -> str:
        """Transcribes audio bytes to text using Deepgram Nova-2."""
        if not self.is_configured:
            return "This is a simulated transcription in development mode."

        url = "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true"
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": mimetype
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, headers=headers, content=audio_bytes)
                if resp.status_code == 200:
                    data = resp.json()
                    channels = data.get("results", {}).get("channels", [])
                    if channels and channels[0].get("alternatives"):
                        return channels[0]["alternatives"][0].get("transcript", "")
                    return ""
                else:
                    logger.error("Deepgram STT error", status=resp.status_code, body=resp.text)
                    raise ProviderError("Deepgram", f"STT failed with status {resp.status_code}")
        except Exception as e:
            logger.error("Deepgram STT network failure", error=str(e))
            raise ProviderError("Deepgram", str(e))

speech_service = SpeechService()
