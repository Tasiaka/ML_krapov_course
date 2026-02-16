from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import get_current_user
from ..schemas import UserOut
from ...db.models import UserDB


router = APIRouter()


@router.get("/me", response_model=UserOut)
def me(user: UserDB = Depends(get_current_user)):
    return UserOut.model_validate(user)


