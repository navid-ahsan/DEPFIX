"""Abstract base class for LLM adapters."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class LLMAdapter(ABC):
    """Abstract base class for LLM adapters.

    Implementations: Ollama, OpenAI, Anthropic, Hugging Face, etc.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize adapter with configuration.

        Args:
            config: Configuration dictionary (host, model, temperature, etc.)
        """
        self.config = config
        self.is_connected = False
        self.model = config.get("model", "default-model")

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to LLM service.

        Returns:
            True if connection successful
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from LLM service.

        Returns:
            True if disconnection successful
        """
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> str:
        """Generate text from prompt.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)
            stream: Whether to stream response

        Returns:
            Generated text
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> str:
        """Generate from chat message format.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        pass

    @abstractmethod
    async def list_models(self) -> List[str]:
        """List available models.

        Returns:
            List of model names
        """
        pass

    @abstractmethod
    async def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get information about a model.

        Args:
            model_name: Name of model

        Returns:
            Model info dict
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if LLM service is healthy.

        Returns:
            True if healthy
        """
        pass
