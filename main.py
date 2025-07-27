import json
import importlib
import logging.config
import os
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi.responses import FileResponse
import yaml
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
import redis.asyncio as aioredis

# YAML 파일 경로
LOGGING_CONFIG_PATH = Path(__file__).resolve().parent / "app_logging_config.yaml"

# YAML 파일에서 로깅 설정 로드
def setup_logging():
    """
    YAML 파일에서 로깅 설정을 로드합니다.

    Args:
        None

    Returns:
        None

    Raises:
        FileNotFoundError: YAML 파일이 존재하지 않을 경우.
        yaml.YAMLError: YAML 파일 파싱 중 오류가 발생한 경우.
    """
    with open(LOGGING_CONFIG_PATH, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
        logging.config.dictConfig(config)

# 로깅 설정 초기화
setup_logging()

# 로거 생성
logger = logging.getLogger(__name__)

# Lifespan 이벤트 핸들러 정의
@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    FastAPI 애플리케이션의 lifespan 이벤트를 처리합니다.

    이 함수는 애플리케이션이 시작되고 메인 로직이 실행되기 전, 그리고 종료되기 전에 필요한 로직을 삽입하기 위해 사용됩니다.

    Args:
        _app (FastAPI): FastAPI 애플리케이션 인스턴스.

    Yields:
        None: 애플리케이션 실행 중에 lifespan 이벤트를 처리합니다.

    Raises:
        None
    """
    # 애플리케이션 시작 시 실행
    logger.info("애플리케이션 시작")
    # Redis pubsub listener를 lifespan 시작 시 실행
    task = asyncio.create_task(redis_pubsub_listener())
    try:
        yield  # 애플리케이션 실행 중
    finally:
        # lifespan 종료 시 Redis pubsub listener도 종료
        task.cancel()
        logger.info("애플리케이션 종료")

# FastAPI 애플리케이션 생성
app = FastAPI(lifespan=lifespan)

# 정적 파일 서빙 (React build 결과물)
app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")
app.mount("/frontend", StaticFiles(directory="frontend/dist"), name="frontend_root")

# API 라우터 등록
# routers 디렉토리에서 모든 라우터 파일을 자동으로 로드
ROUTERS_DIR = "backend/routers"
for filename in os.listdir(ROUTERS_DIR):
    if filename.endswith(".py") and filename != "__init__.py":
        MODULE_NAME = f"{ROUTERS_DIR}.{filename[:-3]}".replace("/", ".")
        module = importlib.import_module(MODULE_NAME)
        app.include_router(module.router, prefix="/api")
        
@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    """
    모든 경로에 대해 React 애플리케이션의 index.html 파일을 반환합니다.
    FastAPI는 먼저 등록된 라우트가 우선 적용되기 때문에 해당 라우트는 마지막에 정의되어야 합니다.
    """
    return FileResponse("frontend/dist/index.html")

# Redis 클라이언트 생성 (글로벌 네임스페이스)
redis_host = os.getenv('REDIS_HOST')
if redis_host is None:
    raise ValueError("Environment variable 'REDIS_HOST' is not set.")

connected_clients = set()

async def redis_pubsub_listener():
    redis = aioredis.from_url(f"redis://{redis_host}:6379/1")
    pubsub = redis.pubsub()
    await pubsub.subscribe("exchange_rate")
    
    async for message in pubsub.listen():
        if message["type"] == "message":
            raw_data = message["data"].decode()
            try:
                # JSON 역직렬화 시도
                data = json.loads(raw_data)
            except Exception:
                # 역직렬화 실패 시 원본 문자열 그대로 사용
                data = raw_data
            # 연결된 모든 클라이언트에게 전송 (항상 문자열로 전송)
            await broadcast_to_clients(json.dumps(data, ensure_ascii=False))

async def broadcast_to_clients(message: str):
    for ws in connected_clients.copy():
        try:
            await ws.send_text(message)
        except Exception:
            connected_clients.remove(ws)



@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        connected_clients.remove(websocket)
       
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
