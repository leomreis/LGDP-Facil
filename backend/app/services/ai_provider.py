"""Camada fina de abstração sobre o provedor de IA.

Existe para que a migração Gemini -> Anthropic (prevista para quando o produto
gerar receita) seja uma troca de variável de ambiente, não uma reescrita. Todo o
resto do código depende só de `AIProvider.generate`.
"""

import logging
from abc import ABC, abstractmethod

import requests

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 60


class AIProviderError(RuntimeError):
    """Falha ao gerar texto. Tratada pelo chamador — nunca vaza para o cliente da API."""


class AIProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Recebe o prompt já montado e devolve o texto gerado."""


class GeminiProvider(AIProvider):
    """Fase de validação: tier gratuito do Google AI Studio."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def generate(self, prompt: str) -> str:
        if not self._api_key:
            raise AIProviderError("GEMINI_API_KEY não configurada")

        try:
            response = requests.post(
                f"{self.BASE_URL}/{self._model}:generateContent",
                headers={"x-goog-api-key": self._api_key},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            corpo = response.json()
        except requests.RequestException as erro:
            raise AIProviderError(f"falha ao chamar o Gemini: {erro}") from erro

        try:
            return corpo["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as erro:
            # Resposta bloqueada por filtro de segurança chega sem 'candidates'.
            raise AIProviderError(f"resposta inesperada do Gemini: {corpo}") from erro


class AnthropicProvider(AIProvider):
    """Fase paga: melhor qualidade em texto jurídico/formal."""

    BASE_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def generate(self, prompt: str) -> str:
        if not self._api_key:
            raise AIProviderError("ANTHROPIC_API_KEY não configurada")

        try:
            response = requests.post(
                self.BASE_URL,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self._model,
                    "max_tokens": 4096,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            corpo = response.json()
        except requests.RequestException as erro:
            raise AIProviderError(f"falha ao chamar a Anthropic: {erro}") from erro

        try:
            return corpo["content"][0]["text"]
        except (KeyError, IndexError) as erro:
            raise AIProviderError(f"resposta inesperada da Anthropic: {corpo}") from erro


class FakeProvider(AIProvider):
    """Usado em teste e desenvolvimento local: não gasta cota nem exige rede."""

    def generate(self, prompt: str) -> str:
        return (
            "[relatório gerado pelo provedor fake — configure AI_PROVIDER para "
            f"usar IA de verdade]\n\nPrompt recebido com {len(prompt)} caracteres."
        )


def get_ai_provider(settings: Settings | None = None) -> AIProvider:
    settings = settings or get_settings()
    escolha = settings.ai_provider.lower()

    if escolha == "gemini":
        return GeminiProvider(settings.gemini_api_key, settings.gemini_model)
    if escolha == "anthropic":
        return AnthropicProvider(settings.anthropic_api_key, settings.anthropic_model)
    if escolha == "fake":
        return FakeProvider()

    raise AIProviderError(f"AI_PROVIDER desconhecido: {settings.ai_provider}")
