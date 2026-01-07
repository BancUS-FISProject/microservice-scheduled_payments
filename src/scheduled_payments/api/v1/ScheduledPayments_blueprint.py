from quart import Blueprint, request
from quart_schema import validate_request, validate_response, tag
from ...models.ScheduledPayments import ScheduledPaymentCreate, ScheduledPaymentUpdate, ScheduledPaymentView, ScheduledPaymentUpcomingView
from ...services.ScheduledPayments_service import ScheduledPaymentService, AccountNotFoundError, SubscriptionLimitReachedError
from logging import getLogger
from typing import List
from ...core.config import settings
from datetime import datetime, timezone
from ...core import extensions as ext

logger = getLogger(__name__)
logger.setLevel(settings.LOG_LEVEL)

bp = Blueprint("scheduled_payments_v1", __name__, url_prefix="/v1/scheduled-payments")

@bp.post("/")
@validate_request(ScheduledPaymentCreate)
@validate_response(ScheduledPaymentView, 201)
@tag(["v1"])
async def create_scheduled_payments(data: ScheduledPaymentCreate):
    
    service = ScheduledPaymentService()

    try:
        new_scheduled_payment = await service.create_new_scheduled_payment(data)
    except AccountNotFoundError:
        return {"error": "La cuenta no existe"}, 404
    except SubscriptionLimitReachedError as e:
        return {"error": f"Límite de pagos programados alcanzado para el plan {e.subscription} (máximo {e.limit})."}, 403
    except Exception as e:
        logger.exception("Error creando pago programado")
        return {"error": "No se pudo crear el pago programado"}, 503

    if not new_scheduled_payment:
        return {"error": "Ya existe un pago programado con ese id"}, 409
    
    return new_scheduled_payment

@bp.get("/<string:scheduled_payment_id>")
@validate_response(ScheduledPaymentView)
@tag(["v1"])
async def get_scheduled_payment(scheduled_payment_id: str):
    
    service = ScheduledPaymentService()
    scheduled_payment = await service.get_scheduled_payment_by_id(scheduled_payment_id)
    
    if not scheduled_payment:
        return {"error": "Pago programado no encontrado"}, 404
    
    return scheduled_payment


@bp.patch("/<string:scheduled_payment_id>")
@validate_request(ScheduledPaymentUpdate)
@validate_response(ScheduledPaymentView)
@tag(["v1"])
async def update_scheduled_payment(scheduled_payment_id: str, data: ScheduledPaymentUpdate):
    
    service = ScheduledPaymentService()
    updated_scheduled_payment = await service.update_scheduled_payment_details(scheduled_payment_id, data)
    
    if not updated_scheduled_payment:
        return {"error": "Pago programado no encontrado"}, 404
    
    return updated_scheduled_payment

@bp.delete("/<string:scheduled_payment_id>")
@tag(["v1"])
async def delete_scheduled_payment(scheduled_payment_id: str):
    
    service = ScheduledPaymentService()
    deleted = await service.delete_scheduled_payment(scheduled_payment_id)
    
    if not deleted:
        return {"error": "Pago programado no encontrado"}, 404
    
    return "", 204

@bp.get("/accounts/<string:account_id>")
@validate_response(List[ScheduledPaymentView])
@tag(["v1"])
async def get_scheduled_payments_by_account(account_id: str):
    service = ScheduledPaymentService()
    payments = await service.get_scheduled_payments_by_account_id(account_id)
    return payments

@bp.get("/health")
@tag(["v1"])
async def health_check():

    return {"status": "ok", "service": "scheduled-payments"}, 200

@bp.get("/accounts/<string:account_id>/upcoming")
@validate_response(list[ScheduledPaymentUpcomingView])
@tag(["v1"])
async def get_upcoming_payments(account_id: str):
    service = ScheduledPaymentService()

    limit_raw = request.args.get("limit", "10")
    try:
        limit = int(limit_raw)
    except ValueError:
        return {"error": "limit debe ser un entero"}, 400

    if limit < 1 or limit > 100:
        return {"error": "limit debe estar entre 1 y 100"}, 400

    now = ext.ntp_clock.now_utc() if ext.ntp_clock else datetime.now(timezone.utc)

    upcoming = await service.get_upcoming_payments_for_account(account_id, now, limit)

    return upcoming