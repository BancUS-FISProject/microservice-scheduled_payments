from ..models.ScheduledPayments import ScheduledPaymentCreate, ScheduledPaymentUpdate, ScheduledPaymentView

class ScheduledPaymentRepository:
    """
    
    """
    def __init__(self, db):
        self.collection = db["scheduled_payments"]
    
    async def insert_scheduled_payment(self, data: ScheduledPaymentCreate) -> ScheduledPaymentView:
        scheduled_payment_doc = data.model_dump(by_alias=True)
        
        result = await self.collection.insert_one(scheduled_payment_doc)
        created_doc = await self.collection.find_one({"_id": result.inserted_id})
        
        created_doc["_id"] = str(created_doc["_id"])
        
        return ScheduledPaymentView.model_validate(created_doc)
    
    async def find_scheduled_payment_by_id(self, scheduled_payment_id: str) -> ScheduledPaymentView | None:
        doc = await self.collection.find_one({"id": scheduled_payment_id})
        
        if doc:
            doc["_id"] = str(doc["_id"])
            return ScheduledPaymentView.model_validate(doc)
        return None
    
    async def update_scheduled_payment(self, scheduled_payment_id: str, data: ScheduledPaymentUpdate) -> ScheduledPaymentView | None:
        update_data = data.model_dump(exclude_unset=True, exclude_none=True)
        
        if not update_data:
            return await self.find_scheduled_payment_by_id(scheduled_payment_id)
        
        await self.collection.update_one(
            {"id": scheduled_payment_id},
            {"$set": update_data}
            )
        
        return await self.find_scheduled_payment_by_id(scheduled_payment_id)
    
    async def delete_scheduled_payment(self, scheduled_payment_id: str) -> bool:
        result = await self.collection.delete_one(
            {"id": scheduled_payment_id}
        )

        return result.deleted_count == 1