from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.models.users import User
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """O frontend usa isto para saber se o onboarding já foi concluído: 401/403
    quando não, 200 com os dados do usuário quando sim."""
    return current_user
