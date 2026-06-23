"""
Модуль маршрутизации (API Router) для работы с пользователями.

Предоставляет эндпоинты для получения информации о текущем
авторизованном пользователе на основе JWT-токена.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user, CurrentUser


router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=CurrentUser,
    summary="Получение профиля текущего пользователя",
    description=(
        "Возвращает данные текущего авторизованного пользователя на основе JWT. "
        "Используется фронтендом для отображения информации в интерфейсе "
        "и проверки прав доступа (is_admin)."
    ),
)
async def read_users_me(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """
    Возвращает профиль текущего авторизованного пользователя.

    Эндпоинт используется после успешной аутентификации для:
    - отображения имени пользователя и отдела в шапке приложения;
    - получения информации о роли (обычный пользователь / администратор);
    - принятия решений о доступности тех или иных элементов интерфейса (RBAC).

    Args:
        current_user: Объект текущего пользователя, внедряемый через зависимость
                      `get_current_user` (извлекается из JWT-токена).

    Returns:
        CurrentUser: Pydantic-модель с данными пользователя (username, is_admin, department и др.).
    """
    return current_user
