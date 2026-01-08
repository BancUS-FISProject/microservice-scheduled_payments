from ..models.ScheduledPayments import ScheduledPaymentCreate, ScheduledPaymentUpdate, ScheduledPaymentView, ScheduledPaymentUpcomingView
from ..db.ScheduledPaymentsRepository import ScheduledPaymentRepository
from ..core import extensions as ext
from datetime import datetime, timezone
import httpx
from logging import getLogger
from ..core.config import settings
from ..models.ScheduledPayments import OnceSchedule
from urllib.parse import quote

logger = getLogger(__name__)
logger.setLevel(settings.LOG_LEVEL)

class AccountNotFoundError(Exception):
    pass

class SubscriptionLimitReachedError(Exception):
    def __init__(self, subscription: str, limit: int):
        self.subscription = subscription
        self.limit = limit
        super().__init__(f"Límite alcanzado para plan {subscription}: {limit}")
class ScheduledPaymentService:
    def __init__(self, repository: ScheduledPaymentRepository | None = None):
        self.repo = repository or ScheduledPaymentRepository(ext.db)
    
    async def create_new_scheduled_payment(self, data: ScheduledPaymentCreate) -> ScheduledPaymentView:

        subscription = await self._get_account_subscription(data.accountId)

        limit = 1
        current_active = None

        match subscription:
            case "basico":
                limit = settings.SUBSCRIPTION_BASIC
            case "premium":
                limit = settings.SUBSCRIPTION_STUDENT
            case "pro":
                limit = settings.SUBSCRIPTION_PRO
            case _:
                limit = settings.SUBSCRIPTION_BASIC

        if limit and limit > 0:
            current_active = await self.repo.count_active_payments_by_account_id(data.accountId)
            if current_active >= limit:
                raise SubscriptionLimitReachedError(subscription, limit)  
            
        new_scheduled_payment_doc = await self.repo.insert_scheduled_payment(data)

        logger.info("Validando límite de suscripción (accountId=%s subscription=%s)", data.accountId, subscription)
        logger.debug("Pagos activos actuales=%s límite=%s", current_active, limit)
        
        return new_scheduled_payment_doc
    
    async def get_scheduled_payment_by_id(self, scheduled_payment_id: str) -> ScheduledPaymentView | None:
        return await self.repo.find_scheduled_payment_by_id(scheduled_payment_id)
    
    async def update_scheduled_payment_details(self, scheduled_payment_id: str, data: ScheduledPaymentUpdate) -> ScheduledPaymentView | None:
        return await self.repo.update_scheduled_payment(scheduled_payment_id, data)
    
    async def delete_scheduled_payment(self, scheduled_payment_id: str) -> bool:
        return await self.repo.delete_scheduled_payment(scheduled_payment_id)
    
    async def get_scheduled_payments_by_account_id(self, account_id: str) -> list[ScheduledPaymentView]:
        return await self.repo.find_payments_by_account_id(account_id)
    
    async def process_due_payments(self) -> None:
        now = ext.ntp_clock.now_utc() if ext.ntp_clock else datetime.now(timezone.utc)

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

                headers = {}
                if getattr(p, "authToken", None):
                    headers["Authorization"] = p.authToken

                resp = await client.post(settings.TRANSFER_SERVICE_URL, json=payload, headers=headers)

                if 200 <= resp.status_code < 300:
                    deactivate = isinstance(p.schedule, OnceSchedule)
                    await self.repo.mark_once_payment_executed(p.id, now, deactivate)
                else:
                    logger.error(
                        f"Transfer service error for payment {p.id}: {resp.status_code} {resp.text}"
                    )

    async def get_upcoming_payments_for_account(
        self,
        account_id: str,
        now: datetime,
        limit: int
    ) -> list[ScheduledPaymentUpcomingView]:
        return await self.repo.find_upcoming_payments_for_account(account_id, now, limit)

    async def _get_account_subscription(self, account_id: str) -> str:
        url = settings.ACCOUNTS_SERVICE_URL.replace("{iban}", quote(account_id, safe=""))
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)

        if resp.status_code == 404:
            logger.warning("Accounts service: cuenta no encontrada (account_id=%s)", account_id)
            raise AccountNotFoundError()

        if resp.status_code >= 400:
            logger.error(
            f"Accounts service error (account_id={account_id} url={url}): "
            f"{resp.status_code} {resp.text}"
        )
            raise RuntimeError(f"Accounts service error: {resp.status_code} {resp.text}")

        data = resp.json()
        sub = (data.get("subscription") or "").lower()
        logger.debug("Subscripción solicitada: ", data, sub)

        if sub not in ["basico", "premium", "pro"]:
            sub = "basico"

        return sub