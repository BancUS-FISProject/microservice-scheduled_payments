from ..models.ScheduledPayments import ScheduledPaymentCreate, ScheduledPaymentUpdate, ScheduledPaymentView, OnceSchedule, WeeklySchedule, MonthlySchedule
from datetime import datetime, timezone

class ScheduledPaymentRepository:
    """
    
    """
    def __init__(self, db):
        self.collection = db["scheduled_payments"]
    
    async def insert_scheduled_payment(self, data: ScheduledPaymentCreate) -> ScheduledPaymentView | None:
        existing = await self.collection.find_one({"id": data.id})
        
        if existing:
            return None
        
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
    
    async def find_payments_to_execute(self, now: datetime) -> list[ScheduledPaymentView]:
        cursor = self.collection.find({"isActive": True})

        results: list[ScheduledPaymentView] = []
        async for doc in cursor:
            payment = ScheduledPaymentView.model_validate(doc)

            if self._should_execute(payment, now):
                results.append(payment)

        return results

    def _should_execute(self, payment: ScheduledPaymentView, now: datetime) -> bool:
        sched = payment.schedule
        now = self._to_utc_aware(now)
        today = now.date()

        # ONCE
        if isinstance(sched, OnceSchedule):
            if payment.lastExecutionAt is not None:
                return False
            exec_dt = self._to_utc_aware(sched.executionDate)
            return exec_dt <= now

        # MONTHLY
        if isinstance(sched, MonthlySchedule):
            start = self._to_utc_aware(sched.startDate)
            end = self._to_utc_aware(sched.endDate)
            if now < start or now > end:
                return False

            if payment.lastExecutionAt:
                last = self._to_utc_aware(payment.lastExecutionAt)
                if last.date() == today:
                    return False

            return now.day == sched.dayOfMonth

        # WEEKLY
        if isinstance(sched, WeeklySchedule):
            start = self._to_utc_aware(sched.startDate)
            end = self._to_utc_aware(sched.endDate)
            if now < start or now > end:
                return False

            if payment.lastExecutionAt:
                last = self._to_utc_aware(payment.lastExecutionAt)
                if last.date() == today:
                    return False

            weekday_name = now.strftime("%A").upper()
            days = [d.upper() for d in sched.daysOfWeek]

            return weekday_name in days

        return False

    async def mark_once_payment_executed(self, scheduled_payment_id: str, execution_time: datetime, deactivate: bool) -> None:
        update = {"lastExecutionAt": execution_time}
        if deactivate:
            update["isActive"] = False

        await self.collection.update_one(
            {"id": scheduled_payment_id},
            {"$set": update},
        )

    def _to_utc_aware(self, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)