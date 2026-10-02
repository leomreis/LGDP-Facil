"""Configuração da aplicação, lida de variáveis de ambiente.

Centralizar aqui evita `os.environ` espalhado e dá um único ponto para o teste
sobrescrever configuração.
"""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.supabase_url: str = os.getenv("SUPABASE_URL", "")
        self.supabase_jwks_url: str = os.getenv("SUPABASE_JWKS_URL", "")
        # Chave de serviço: usada só para convidar membros de equipe via
        # Supabase Admin API. Nunca deve rodar no frontend.
        self.supabase_secret_key: str = os.getenv("SUPABASE_SECRET_KEY", "")
        # O Supabase emite tokens com aud="authenticated" para usuário logado.
        self.jwt_audience: str = os.getenv("SUPABASE_JWT_AUDIENCE", "authenticated")

        # Vazio = sem fila real configurada; scans caem para BackgroundTasks do
        # FastAPI (útil em dev/CI sem Redis rodando). Ver app/core/queue.py.
        self.redis_url: str = os.getenv("REDIS_URL", "")

        # Origens autorizadas a chamar a API pelo navegador (CORS). Lista
        # separada por vírgula; default cobre o Vite em dev.
        origens = os.getenv("CORS_ORIGINS", "http://localhost:5173")
        self.cors_origins: list[str] = [o.strip() for o in origens.split(",") if o.strip()]

        self.ai_provider: str = os.getenv("AI_PROVIDER", "fake")
        self.gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
        self.gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self.anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
        self.anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

        # Observabilidade — vazio = desligado. Nunca falha a inicialização da
        # app por falta dessas variáveis; só significa "sem monitoramento".
        self.sentry_dsn: str = os.getenv("SENTRY_DSN", "")
        self.environment: str = os.getenv("ENVIRONMENT", "development")


@lru_cache
def get_settings() -> Settings:
    return Settings()
