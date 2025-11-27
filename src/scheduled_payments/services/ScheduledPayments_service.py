from ..models.ScheduledPayments import ScheduledPaymentCreate, ScheduledPaymentUpdate, ScheduledPaymentView
from ..db.ScheduledPaymentsRepository import ScheduledPaymentRepository
from ..core import extensions as ext


class ScheduledPaymentService:
    def __init__(self, repository: ScheduledPaymentRepository | None = None):
        self.repo = repository or ScheduledPaymentRepository(ext.db)
    
    async def create_new_scheduled_payment(self, data: ScheduledPaymentCreate) -> ScheduledPaymentView:
        # Business logic here
  
        new_scheduled_payment_doc = await self.repo.insert_scheduled_payment(data)
        
        return new_scheduled_payment_doc
    
    async def get_scheduled_payment_by_id(self, scheduled_payment_id: str) -> ScheduledPaymentView | None:
        return await self.repo.find_scheduled_payment_by_id(scheduled_payment_id)
    
    async def update_scheduled_payment_details(self, scheduled_payment_id: str, data: ScheduledPaymentUpdate) -> ScheduledPaymentView | None:
        return await self.repo.update_scheduled_payment(scheduled_payment_id, data)
    
    async def delete_scheduled_payment(self, scheduled_payment_id: str) -> bool:
        return await self.repo.delete_scheduled_payment(scheduled_payment_id)