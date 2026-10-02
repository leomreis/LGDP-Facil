"""Validação do JWT emitido pelo Supabase Auth.

O projeto assina com chave assimétrica (ECC P-256), então a verificação usa a
chave pública publicada no JWKS — e não um segredo compartilhado. Consequência
prática: rotacionar a chave de assinatura no Supabase não exige redeploy da API,
basta o cache do JWKS expirar.
"""

import logging
import uuid
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.models.users import User

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)

# O PyJWKClient já faz cache das chaves; um cliente por URL evita buscar o JWKS a
# cada requisição.
_jwks_clients: dict[str, PyJWKClient] = {}

CREDENCIAIS_INVALIDAS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Token inválido ou expirado",
    headers={"WWW-Authenticate": "Bearer"},
)


def _jwks_client(jwks_url: str) -> PyJWKClient:
    if jwks_url not in _jwks_clients:
        _jwks_clients[jwks_url] = PyJWKClient(jwks_url, cache_keys=True)
    return _jwks_clients[jwks_url]


def decode_token(token: str, settings: Settings) -> dict[str, Any]:
    """Decodifica e valida assinatura, expiração e audience do token."""
    if not settings.supabase_jwks_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_JWKS_URL não configurada",
        )

    try:
        signing_key = _jwks_client(settings.supabase_jwks_url).get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience=settings.jwt_audience,
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError as erro:
        # Log detalhado só no servidor — a resposta ao cliente continua genérica
        # de propósito (não vazar detalhe de validação de token).
        logger.warning("Falha ao validar token: %s: %s", type(erro).__name__, erro)
        raise CREDENCIAIS_INVALIDAS from erro


def get_authenticated_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Valida o token sem exigir usuário local — usado só no onboarding, o único
    momento em que um token válido do Supabase ainda não tem `users` correspondente."""
    if credentials is None:
        raise CREDENCIAIS_INVALIDAS
    return decode_token(credentials.credentials, settings)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """Dependency das rotas protegidas: token válido -> usuário local correspondente.

    O usuário é criado no Supabase Auth, não aqui. A tabela `users` guarda o
    vínculo com a empresa, que o Supabase não conhece — por isso um usuário
    autenticado mas ainda sem empresa recebe 403, não 401: a credencial é válida,
    falta o onboarding.
    """
    if credentials is None:
        raise CREDENCIAIS_INVALIDAS

    claims = decode_token(credentials.credentials, settings)

    try:
        user_id = uuid.UUID(claims["sub"])
    except (KeyError, ValueError) as erro:
        raise CREDENCIAIS_INVALIDAS from erro

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário autenticado ainda não vinculado a uma empresa",
        )

    return user
