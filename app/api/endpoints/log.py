import logging
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

logger = logging.getLogger(__name__)

@router.put("/log")
def update_log_level(file_name: str = Query(..., description="The name of the file/module"), level: str = Query(..., description="The log level to set")):
    """
    특정 파일/모듈의 로그 레벨을 변경합니다.

    Args:
        file_name (str): 로그 레벨을 변경할 파일 또는 모듈의 이름.
        level (str): 설정할 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Returns:
        dict: 로그 레벨이 성공적으로 변경되었음을 나타내는 메시지.

    Raises:
        HTTPException: 로그 레벨이 유효하지 않거나 파일/모듈이 존재하지 않을 경우.
    """
    level = level.upper()
    if level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        raise HTTPException(status_code=400, detail="Invalid log level")

    file_logger = logging.getLogger(f"app.api.endpoints.{file_name}")
    log_level = getattr(logging, level, None)
    if log_level is None:
        raise HTTPException(status_code=400, detail="Invalid log level")
    file_logger.setLevel(log_level)
    logger.info("Log level changed to %s for %s", level, file_logger.name)
    return {"success": "OK"}
