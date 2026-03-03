"""Ollama LLM adapter implementation."""

import httpx
import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable
from .base import LLMAdapter

logger = logging.getLogger(__name__)


class OllamaLLMAdapter(LLMAdapter):
    """Ollama LLM adapter for local model serving.

    Uses Ollama API for generating text with local models.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize Ollama LLM adapter.

        Args:
            config: Must contain:
                - host: Ollama server host (default: http://localhost:11434)
                - model: Model name (e.g., 'llama2', 'mistral')
                - temperature: Sampling temperature (default: 0.7)
                - timeout: Request timeout in seconds (default: 300)
        """
        super().__init__(config)
        self.host = config.get("host", "http://localhost:11434")
        self.temperature = config.get("temperature", 0.7)
        self.timeout = config.get("timeout", 300)
        self.client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> bool:
        """Connect to Ollama service.

        Returns:
            True if connection successful
        """
        try:
            self.client = httpx.AsyncClient(timeout=self.timeout)
            health = await self.health_check()

            if health:
                self.is_connected = True
                logger.info(f"Connected to Ollama at {self.host}")
                return True
            else:
                logger.error(f"Ollama health check failed at {self.host}")
                return False

        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            return False

    async def disconnect(self) -> bool:
        """Disconnect from Ollama service.

        Returns:
            True if disconnection successful
        """
        try:
            if self.client:
                await self.client.aclose()
                self.is_connected = False
                logger.info("Disconnected from Ollama")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from Ollama: {e}")
            return False

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> str:
        """Generate text from prompt using Ollama.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens (Ollama uses different param)
            temperature: Sampling temperature
            stream: Whether to stream (handled in generate_stream)

        Returns:
            Generated text
        """
        if not self.is_connected or not self.client:
            logger.error("Not connected to Ollama")
            return ""

        try:
            response = await self.client.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "temperature": temperature,
                    "stream": False,
                },
            )

            if response.status_code != 200:
                logger.error(f"Ollama error: {response.status_code}")
                return ""

            # Parse response (streaming in Ollama returns JSONL)
            lines = response.text.strip().split("\n")
            text = ""
            for line in lines:
                if line:
                    import json
                    data = json.loads(line)
                    text += data.get("response", "")

            return text

        except Exception as e:
            logger.error(f"Error generating with Ollama: {e}")
            return ""

    async def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        callback: Optional[Callable[[str], Any]] = None,
    ) -> str:
        """Generate text with streaming.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens
            temperature: Sampling temperature
            callback: Callback for each token

        Returns:
            Full generated text
        """
        if not self.is_connected or not self.client:
            logger.error("Not connected to Ollama")
            return ""

        try:
            full_text = ""

            async with self.client.stream(
                "POST",
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "temperature": temperature,
                    "stream": True,
                },
            ) as response:
                import json

                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        token = data.get("response", "")
                        full_text += token

                        if callback:
                            await callback(token)

            return full_text

        except Exception as e:
            logger.error(f"Error streaming generation: {e}")
            return ""

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> str:
        """Generate from chat messages (converts to prompt).

        Args:
            messages: List of {'role': 'user/assistant', 'content': '...'}
            max_tokens: Maximum tokens
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        # Convert to prompt format
        prompt = ""
        for msg in messages:
            role = msg.get("role", "user").upper()
            content = msg.get("content", "")
            prompt += f"{role}: {content}\n"

        prompt += "ASSISTANT:"

        return await self.generate(prompt, max_tokens, temperature)

    async def list_models(self) -> List[str]:
        """List available models in Ollama.

        Returns:
            List of model names
        """
        if not self.is_connected or not self.client:
            return []

        try:
            response = await self.client.get(f"{self.host}/api/tags")

            if response.status_code == 200:
                import json
                data = json.loads(response.text)
                models = [m["name"] for m in data.get("models", [])]
                return models

            return []

        except Exception as e:
            logger.error(f"Error listing Ollama models: {e}")
            return []

    async def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get information about a model.

        Args:
            model_name: Name of model

        Returns:
            Model info dict
        """
        if not self.is_connected or not self.client:
            return {}

        try:
            response = await self.client.post(
                f"{self.host}/api/show",
                json={"name": model_name},
            )

            if response.status_code == 200:
                import json
                return json.loads(response.text)

            return {}

        except Exception as e:
            logger.error(f"Error getting model info: {e}")
            return {}

    async def health_check(self) -> bool:
        """Check if Ollama service is running.

        Returns:
            True if healthy
        """
        try:
            if not self.client:
                return False

            response = await self.client.get(f"{self.host}/api/tags", timeout=5)
            return response.status_code == 200

        except Exception as e:
            logger.debug(f"Ollama health check failed: {e}")
            return False
