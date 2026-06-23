"""
Модуль маршрутизации (API Router) для импорта исторических данных.

Предоставляет эндпоинты для загрузки и обработки файлов Excel (.xlsx),
содержащих legacy-данные (ранее зарегистрированные документы и оборудование).

Используется для первоначального наполнения базы данных при миграции
с устаревших систем. Автоматически сдвигает глобальный счетчик номеров,
чтобы избежать конфликтов с новыми регистрациями.
"""

from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from app.core.db import lifespan_session
from app.core.auth import get_current_user, CurrentUser
from app.services.importer import ExcelImporterService


router = APIRouter(prefix="/import", tags=["Import"])


@router.post(
    "/excel",
    response_model=dict,
    summary="Импорт документов из Excel (только администратор)",
    description=(
        "Принимает файл Excel (.xlsx) с историческими данными, сохраняет его "
        "на диск и передает в сервис импорта. Выполняет парсинг, создание "
        "документов, связанного оборудования и сдвиг глобального счетчика номеров."
    ),
)
async def import_excel(
    file: UploadFile = File(..., description="Файл Excel (.xlsx) с историей регистраций"),
    session: AsyncSession = Depends(lifespan_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """
    Выполняет импорт исторических данных из Excel-файла.

    Процесс включает:
    - проверку прав администратора;
    - сохранение загруженного файла во временную директорию `var/uploads`;
    - вызов `ExcelImporterService`, который парсит файл, создаёт/обновляет
      записи документов и оборудования, а также сдвигает глобальный счетчик
      номеров (`doc_counter`), чтобы новые номера не пересекались с импортированными.

    Примечание: синхронная запись файла на диск приемлема, так как операция
    выполняется редко и только администраторами.

    Args:
        file: Загружаемый Excel-файл (multipart/form-data).
        session: Асинхронная сессия базы данных.
        user: Текущий авторизованный пользователь.

    Returns:
        dict: Статистика импорта (количество обработанных строк, созданных
              документов, оборудования, ошибок и т.д.).

    Raises:
        HTTPException(403): Если пользователь не обладает правами администратора.
        HTTPException(400/422): При ошибках валидации файла или неверном формате.
        HTTPException(500): При внутренних ошибках во время парсинга или сохранения данных.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только админ может импортировать Excel.",
        )

    # Создаем директорию для временного хранения загружаемых файлов
    path = Path("var/uploads")
    path.mkdir(parents=True, exist_ok=True)
    fpath = path / file.filename

    # Сохраняем файл на диск (синхронная запись допустима для разовых задач администратора)
    with open(fpath, "wb") as f:
        f.write(await file.read())

    # Запускаем парсинг и сохранение данных в БД
    service = ExcelImporterService(session)
    result = await service.import_file(str(fpath))

    return result
