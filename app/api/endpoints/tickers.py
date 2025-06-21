# API endpoints for managing common tickers
import logging
from fastapi import APIRouter

router = APIRouter()

logger = logging.getLogger(__name__)

@router.get("/tickers")
def get_tickers():
    logger.info("Fetching list of common tickers")
    logger.debug("xxxxxxxxxxxxxx")
    return {"message": "List of common tickers"}
