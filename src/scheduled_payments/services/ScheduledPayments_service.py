from ..models.ScheduledPayments import ScheduledPaymentCreate, ScheduledPaymentUpdate, ScheduledPaymentView
from ..db.ScheduledPaymentsRepository import ScheduledPaymentRepository
from ..core import extensions as ext
from datetime import datetime, timezone
import httpx
from logging import getLogger
from ..core.config import settings
from ..models.ScheduledPayments import OnceSchedule

logger = getLogger(__name__)
logger.setLevel(settings.LOG_LEVEL)
class ScheduledPaymentService:
    def __init__(self, repository: ScheduledPaymentRepository | None = None):
        self.repo = repository or ScheduledPaymentRepository(ext.db)
    
    async def create_new_scheduled_payment(self, data: ScheduledPaymentCreate) -> ScheduledPaymentView:
  
        new_scheduled_payment_doc = await self.repo.insert_scheduled_payment(data)
        
        return new_scheduled_payment_doc
    
    async def get_scheduled_payment_by_id(self, scheduled_payment_id: str) -> ScheduledPaymentView | None:
        return await self.repo.find_scheduled_payment_by_id(scheduled_payment_id)
    
    async def update_scheduled_payment_details(self, scheduled_payment_id: str, data: ScheduledPaymentUpdate) -> ScheduledPaymentView | None:
        return await self.repo.update_scheduled_payment(scheduled_payment_id, data)
    
    async def delete_scheduled_payment(self, scheduled_payment_id: str) -> bool:
        return await self.repo.delete_scheduled_payment(scheduled_payment_id)
    
    async def process_due_payments(self) -> None:
        now = datetime.now(timezone.utc)

        payments = await self.repo.find_payments_to_execute(now)
        if not payments:
            return

        async with httpx.AsyncClient(timeout=10.0) as client:
            for p in payments:
                payload = {
                    "sender": p.accountId,
                    "receiver": p.beneficiary.iban,
                    "quantity": p.amount.value,
                    "currency": p.amount.currency
                }

                resp = await client.post(settings.TRANSFER_SERVICE_URL, json=payload)

                if resp.status_code in (200, 201):
                    deactivate = isinstance(p.schedule, OnceSchedule)
                    await self.repo.mark_once_payment_executed(p.id, now, deactivate)
                else:
                    logger.error(
                        f"Transfer service error for payment {p.id}: {resp.status_code} {resp.text}"
                    )