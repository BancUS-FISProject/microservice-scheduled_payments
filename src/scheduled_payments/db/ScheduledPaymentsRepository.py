from ..models.ScheduledPayments import ScheduledPaymentCreate, ScheduledPaymentUpdate, ScheduledPaymentView, OnceSchedule, WeeklySchedule, MonthlySchedule, ScheduledPaymentUpcomingView
from datetime import datetime, timezone, timedelta

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
    
    async def find_payments_by_account_id(self, account_id: str) -> list[ScheduledPaymentView]:
        cursor = self.collection.find({"accountId": account_id})
        results: list[ScheduledPaymentView] = []

        async for doc in cursor:
            results.append(ScheduledPaymentView.model_validate(doc))

        return results
    
    async def find_upcoming_payments_for_account(
        self,
        account_id: str,
        now: datetime,
        limit: int
    ) -> list[ScheduledPaymentUpcomingView]:

        now = self._to_utc_aware(now)

        cursor = self.collection.find({"isActive": True, "accountId": account_id})

        upcoming: list[ScheduledPaymentUpcomingView] = []

        async for doc in cursor:
            payment = ScheduledPaymentView.model_validate(doc)
            next_dt = self._next_execution(payment, now)
            if next_dt is None:
                continue

            upcoming.append(
                ScheduledPaymentUpcomingView(**payment.model_dump(), nextExecutionAt=next_dt)
            )

        upcoming.sort(key=lambda p: p.nextExecutionAt)
        return upcoming[:limit]



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
    
    def _next_execution(self, payment: ScheduledPaymentView, now: datetime) -> datetime | None:
        sched = payment.schedule
        now = self._to_utc_aware(now)

        last_exec = self._to_utc_aware(payment.lastExecutionAt) if payment.lastExecutionAt else None

        # ONCE
        if isinstance(sched, OnceSchedule):
            if payment.lastExecutionAt is not None:
                return None
            exec_dt = self._to_utc_aware(sched.executionDate)
            return exec_dt if exec_dt >= now else None

        # MONTHLY
        if isinstance(sched, MonthlySchedule):
            start = self._to_utc_aware(sched.startDate)
            end = self._to_utc_aware(sched.endDate)
            if now < start:
                base = start
            else:
                base = now

            for month_jump in range(0, 3): 
                year = base.year
                month = base.month + month_jump
                while month > 12:
                    month -= 12
                    year += 1

                day = sched.dayOfMonth
                try:
                    candidate = datetime(year, month, day, tzinfo=timezone.utc)
                except ValueError:
                    continue

                if candidate < start or candidate > end:
                    continue
                if candidate < now:
                    continue
                if last_exec and last_exec.date() == candidate.date():
                    continue

                return candidate

            return None

        # WEEKLY
        if isinstance(sched, WeeklySchedule):
            start = self._to_utc_aware(sched.startDate)
            end = self._to_utc_aware(sched.endDate)
            if now > end:
                return None

            base = max(now, start)

            days = [d.upper() for d in sched.daysOfWeek]
            if not days:
                return None

            for i in range(0, 14):
                candidate = (base + timedelta(days=i)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                if candidate > end:
                    break

                weekday_name = candidate.strftime("%A").upper()
                if weekday_name not in days:
                    continue

                if candidate < now:
                    continue

                if last_exec and last_exec.date() == candidate.date():
                    continue

                return candidate

            return None

        return None
