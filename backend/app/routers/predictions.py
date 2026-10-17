import io
import math

import pandas as pd
from fastapi import APIRouter, HTTPException, UploadFile
from sqlmodel import select

from app.db import SessionDep
from app.ml_client import ml_client
from app.models import PredictionLog
from app.schemas import PredictionLogRead, PredictRequest, PredictResponse

router = APIRouter(tags=["predictions"])

MAX_LOGGED_ROWS = 1000  # don't flood the DB on huge batch uploads


async def _predict_and_log(records: list[dict], session: SessionDep) -> PredictResponse:
    result = PredictResponse.model_validate(await ml_client.predict(records))
    for record, pred in zip(records[:MAX_LOGGED_ROWS], result.predictions):
        session.add(
            PredictionLog(
                model_version=result.model_version, input=record, output=pred.model_dump()
            )
        )
    session.commit()
    return result


@router.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest, session: SessionDep) -> PredictResponse:
    return await _predict_and_log(req.records, session)


@router.post("/predict/csv", response_model=PredictResponse)
async def predict_csv(file: UploadFile, session: SessionDep) -> PredictResponse:
    try:
        df = pd.read_csv(io.BytesIO(await file.read()))
    except Exception as e:
        raise HTTPException(400, f"Could not parse CSV: {e}") from e
    if df.empty:
        raise HTTPException(400, "CSV has no rows")
    # NaN isn't valid JSON — send missing values as null.
    records = [
        {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in r.items()}
        for r in df.to_dict(orient="records")
    ]
    return await _predict_and_log(records, session)


@router.get("/predictions", response_model=list[PredictionLogRead])
def list_predictions(session: SessionDep, limit: int = 50, offset: int = 0) -> list[PredictionLog]:
    stmt = (
        select(PredictionLog)
        .order_by(PredictionLog.id.desc())
        .offset(offset)
        .limit(min(limit, 500))
    )
    return list(session.exec(stmt))
