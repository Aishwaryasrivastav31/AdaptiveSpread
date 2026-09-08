from fastapi import APIRouter, HTTPException
import uuid
import logging
from datetime import datetime

from rfq.models import RFQRequest, RFQResponse, RFQOutcome
from rfq.service import RFQService
from storage.database import db

logger = logging.getLogger(__name__)

router = APIRouter()
rfq_service = RFQService()


@router.post("/quote", response_model=RFQResponse)
async def get_quote(request: RFQRequest):
    try:
        logger.info(f"📊 RFQ: {request.pair} - {request.notional} - {request.tier}")
        rfq_id = str(uuid.uuid4())
        quote, context = rfq_service.process_rfq(request.dict(), rfq_id)

        return RFQResponse(
            rfq_id=rfq_id,
            pair=request.pair,
            mid_price=quote.mid_price,
            spread_bps=quote.spread_bps,
            bid=quote.bid,
            ask=quote.ask,
            model=quote.model,
            volatility=quote.volatility,
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/outcome")
async def record_outcome(outcome: RFQOutcome):
    try:
        logger.info(
            f"📝 Outcome: {outcome.rfq_id} - {'Accepted' if outcome.accepted else 'Rejected'}"
        )

        stored_rfq = db.get_rfq(outcome.rfq_id)
        if not stored_rfq:
            raise HTTPException(status_code=404, detail="RFQ not found")

        reward = rfq_service.calculate_reward(
            stored_rfq["final_spread"], outcome.accepted
        )
        rfq_service.update_model(stored_rfq["context"], stored_rfq["arm_idx"], reward)
        db.store_outcome(outcome.rfq_id, outcome.accepted, reward)

        return {"status": "success", "reward": reward}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
