from fastapi import Depends
from backend.db.repository.exchange import ExchangeRepository
from backend.dependencies.auth import get_current_user
from backend.dependencies.injection import get_exchange_repository
from backend.services.exchange_hub import ExchangeHub


def get_exchange_hub(user=Depends(get_current_user), 
                     exchange_repository: ExchangeRepository = Depends(get_exchange_repository)):
    """
    사용자 정보를 기반으로 ExchangeHub 인스턴스를 생성합니다.
    """
    return ExchangeHub(user.id, exchange_repository)