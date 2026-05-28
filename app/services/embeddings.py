"""Embedding provider abstraction."""
from typing import Protocol

from app.core.config import Settings


class EmbeddingProvider(Protocol):
    async def embed_texts(self, texts: list[str]) -> list[list[float]]: ...


class NullEmbeddingProvider:
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return []


class OpenAIEmbeddingProvider:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        response = await client.embeddings.create(model=self.settings.embedding_model, input=texts)
        return [item.embedding for item in response.data]


class EmbeddingService:
    def __init__(self, settings: Settings):
        self.settings = settings
        if settings.embeddings_enabled and settings.embedding_provider == "openai" and settings.openai_api_key:
            self.provider: EmbeddingProvider = OpenAIEmbeddingProvider(settings)
        else:
            self.provider = NullEmbeddingProvider()

    @property
    def enabled(self) -> bool:
        return not isinstance(self.provider, NullEmbeddingProvider)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return await self.provider.embed_texts(texts)
