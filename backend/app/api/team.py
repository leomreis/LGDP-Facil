import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.models.users import User
from app.schemas.team import TeamInviteCreate
from app.schemas.user import UserResponse
from app.services.supabase_admin import SupabaseAdminError, invite_user

router = APIRouter(prefix="/team", tags=["team"])


@router.get("/members", response_model=list[UserResponse])
def list_team_members(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(User).filter(User.company_id == current_user.company_id).all()


@router.post("/invitations", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def invite_team_member(
    payload: TeamInviteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """Convida um novo membro para a mesma empresa.

    Restrito a role="owner": qualquer membro poder convidar ampliaria livremente
    quem acessa os dados da empresa sem nenhum controle.
    """
    if current_user.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Só o dono da empresa pode convidar novos membros",
        )

    if db.query(User).filter(User.email == payload.email).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um usuário com este e-mail",
        )

    try:
        user_id = invite_user(payload.email, settings)
    except SupabaseAdminError as erro:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Não foi possível enviar o convite: {erro}",
        ) from erro

    novo_usuario = User(
        id=user_id,
        company_id=current_user.company_id,
        name=payload.name,
        email=payload.email,
        role="member",
    )
    db.add(novo_usuario)
    try:
        db.commit()
    except IntegrityError as erro:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um usuário com este e-mail",
        ) from erro
    db.refresh(novo_usuario)

    return novo_usuario


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_team_member(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove um membro da empresa (inclusive o próprio owner que está chamando
    — "sair da empresa" é só um caso particular de remoção). O usuário continua
    existindo no Supabase Auth (não é este endpoint que apaga a conta), mas sem
    a linha em `users` ele não passa mais em `get_current_user` — perde acesso.

    Única restrição real: a remoção não pode deixar a empresa sem nenhum owner.
    Isso já cobre "o único owner não pode se remover" como caso particular —
    não precisa de uma regra "não remova a si mesmo" separada, que só
    impediria um owner de sair quando já existe outro para assumir.
    """
    if current_user.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Só o dono da empresa pode remover membros",
        )

    membro = (
        db.query(User)
        .filter(User.id == user_id, User.company_id == current_user.company_id)
        .first()
    )
    if membro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membro não encontrado")

    if membro.role == "owner":
        outros_owners = (
            db.query(User)
            .filter(
                User.company_id == current_user.company_id,
                User.role == "owner",
                User.id != membro.id,
            )
            .count()
        )
        if outros_owners == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A empresa precisa de pelo menos um dono",
            )

    db.delete(membro)
    db.commit()
