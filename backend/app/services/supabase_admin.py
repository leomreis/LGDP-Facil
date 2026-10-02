"""Cliente mínimo da Supabase Admin API — usado só para convidar membros de
equipe. Precisa da service role key (SUPABASE_SECRET_KEY), que nunca deve
rodar no frontend; por isso este cliente só existe no backend.
"""

import requests

from app.core.config import Settings

REQUEST_TIMEOUT_SECONDS = 15


class SupabaseAdminError(RuntimeError):
    """Falha ao chamar a Supabase Admin API. Tratada pelo chamador."""


def invite_user(email: str, settings: Settings) -> str:
    """Cria o usuário no Supabase Auth (não confirmado) e dispara o e-mail de
    convite com link para definir senha. Devolve o id (UUID) do usuário criado.
    """
    if not settings.supabase_url or not settings.supabase_secret_key:
        raise SupabaseAdminError("SUPABASE_URL/SUPABASE_SECRET_KEY não configuradas")

    try:
        response = requests.post(
            f"{settings.supabase_url}/auth/v1/invite",
            headers={
                "apikey": settings.supabase_secret_key,
                "Authorization": f"Bearer {settings.supabase_secret_key}",
                "Content-Type": "application/json",
            },
            json={"email": email},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as erro:
        raise SupabaseAdminError(f"falha ao chamar a Supabase Admin API: {erro}") from erro

    if response.status_code in (400, 422):
        raise SupabaseAdminError(f"e-mail já cadastrado no Supabase: {email}")
    if not response.ok:
        raise SupabaseAdminError(
            f"Supabase Admin API devolveu {response.status_code}: {response.text}"
        )

    corpo = response.json()
    user_id = corpo.get("id")
    if not user_id:
        raise SupabaseAdminError(f"resposta inesperada da Supabase Admin API: {corpo}")

    return user_id
