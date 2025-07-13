import logging
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

logger = logging.getLogger(__name__)