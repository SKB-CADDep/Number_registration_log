"""
Модуль аутентификации и авторизации на основе JWT.

Отвечает за:
    - Извлечение JWT-токена из заголовка Authorization
    - Валидацию и декодирование токена
    - Получение текущего пользователя из базы данных
    - Проверку административных прав

Предоставляет FastAPI-зависимости (Dependencies) для использования в эндпоинтах.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import lifespan_session
from app.services.users import UsersService


# Указываем относительный URL логина (для корректной работы Swagger UI)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class CurrentUser(BaseModel):
    """
    Схема данных текущего авторизованного пользователя.

    Используется как тип возвращаемого значения в зависимостях аутентификации.
    """
    id: int
    username: str
    is_admin: bool


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        session: AsyncSession = Depends(lifespan_session),
) -> CurrentUser:
    """
    Основная зависимость для получения текущего пользователя по JWT-токену.

    Выполняет следующие действия:
        1. Декодирует JWT-токен
        2. Извлекает username из поля 'sub'
        3. Находит или создаёт пользователя через UsersService
        4. Определяет, является ли пользователь администратором

    Raises:
        HTTPException(401): Если токен отсутствует, недействителен или не содержит username.

    Returns:
        CurrentUser: Объект с данными текущего пользователя (id, username, is_admin).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    svc = UsersService(session)
    user = await svc.get_or_create_by_username(username)

    is_admin = user.username.lower() in [u.lower() for u in settings.admin_users]

    return CurrentUser(id=user.id, username=user.username, is_admin=is_admin)


async def get_current_admin_user(
        current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """
    Зависимость для получения текущего пользователя с проверкой прав администратора.

    Используется в тех эндпоинтах, где требуются административные права.

    Raises:
        HTTPException(403): Если у пользователя недостаточно прав (is_admin = False).
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения этого действия.",
        )
    return current_user
