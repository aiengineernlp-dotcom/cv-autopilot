"""Couche : Router (UI HTTP) -- comptes email. Parse la requête, appelle
email_account_service, sérialise. Ne fait jamais : logique métier, requête
SQL, déchiffrer un mot de passe pour l'exposer en réponse."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import get_current_user
from ..db import get_db
from ..models import User
from ..schemas.email_account import ConnectEmailAccountRequest, EmailAccountOut
from ..services import email_account_service

router = APIRouter(prefix="/email-accounts", tags=["email-accounts"])


@router.post("", response_model=EmailAccountOut, status_code=status.HTTP_201_CREATED)
async def connect_email_account(
    payload: ConnectEmailAccountRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> EmailAccountOut:
    try:
        account = await email_account_service.connect(
            db, user_id=current_user.id, label=payload.label, imap_host=payload.imap_host,
            imap_port=payload.imap_port, smtp_host=payload.smtp_host, smtp_port=payload.smtp_port,
            username=payload.username, password=payload.password,
        )
    except email_account_service.EmailAccountError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    return account


@router.get("", response_model=list[EmailAccountOut])
async def list_email_accounts(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await email_account_service.list_accounts(db, current_user.id)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_email_account(
    account_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> None:
    try:
        await email_account_service.delete_account(db, account_id=account_id, user_id=current_user.id)
    except email_account_service.EmailAccountNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
