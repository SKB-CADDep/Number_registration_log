"""
Модуль административного API (Admin Router).

Предоставляет защищённые эндпоинты для выполнения административных операций
и проверки привилегий пользователей. Используется для реализации RBAC
(Role-Based Access Control) на стороне frontend и backend.

В текущей версии содержит функциональность проверки прав администратора.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user, CurrentUser


router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/check-access",
    response_model=dict,
    summary="Проверка прав администратора",
    description=(
        "Проверяет, обладает ли текущий пользователь правами администратора. "
        "Используется фронтендом для условного отображения административного "
        "интерфейса (меню, кнопки и т.д.)."
    ),
)
async def check_access(
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """
    Проверяет наличие административных прав у текущего пользователя.

    Эндпоинт используется в рамках RBAC для определения видимости административных
    элементов интерфейса. При отсутствии прав немедленно возвращает 403 ошибку.

    Args:
        user: Текущий авторизованный пользователь, внедряемый через JWT-зависимость.

    Returns:
        dict: `{"is_admin": true}` в случае успеха.

    Raises:
        HTTPException(403): Если у пользователя недостаточно прав (не администратор).
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен",
        )

    return {"is_admin": True}
