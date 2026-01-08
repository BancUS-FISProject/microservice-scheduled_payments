from quart import Blueprint, request
from quart_schema import validate_request, validate_response, tag
from ...models.ScheduledPayments import ScheduledPaymentCreate, ScheduledPaymentUpdate, ScheduledPaymentView, ScheduledPaymentUpcomingView
from ...services.ScheduledPayments_service import ScheduledPaymentService, AccountNotFoundError, SubscriptionLimitReachedError
from logging import getLogger
from typing import List, Literal
from ...core.config import settings
from datetime import datetime, timezone
from ...core import extensions as ext
from pydantic import BaseModel, Field

logger = getLogger(__name__)
logger.setLevel(settings.LOG_LEVEL)

bp = Blueprint("scheduled_payments_v1", __name__, url_prefix="/v1/scheduled-payments")

class ErrorResponse(BaseModel):
    error: str = Field(..., description="Mensaje de error legible.")
    detail: str | None = Field(None, description="Detalle adicional del error si aplica.")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Estado del servicio (ok/error).")
    service: str = Field(..., description="Nombre del servicio.")

class DeleteResponse(BaseModel):
    status: Literal["deleted"] = Field("deleted", description="Confirmación de borrado.")
    id: str = Field(..., description="ID del pago programado eliminado.")

@bp.post("/")
@validate_request(ScheduledPaymentCreate)
@validate_response(ScheduledPaymentView, 201)
@validate_response(ErrorResponse, 401)
@validate_response(ErrorResponse, 403)
@validate_response(ErrorResponse, 404)
@validate_response(ErrorResponse, 409)
@validate_response(ErrorResponse, 503)
@tag(["v1"])
async def create_scheduled_payments(data: ScheduledPaymentCreate):
    """
    Crea un pago programado.

    Reglas principales:
    - Requiere cabecera Authorization (se guarda en el pago para poder ejecutar transferencias después).
    - Valida que la cuenta exista consultando el Accounts Service.
    - Aplica el límite de pagos activos en función del plan de suscripción (basic/student/pro).
    - Si el `id` ya existe, devuelve 409.

    Respuestas típicas:
    - 201: Pago programado creado correctamente.
    - 401: No se envió token de autorización.
    - 404: La cuenta no existe.
    - 403: Límite de pagos alcanzado según suscripción.
    - 409: Ya existe un pago con ese id.
    - 503: Error del servicio (dependencias o DB).
    """

    token = request.headers.get("Authorization")
    logger.debug(f"Token recibido: {token}")
    if not token:
        logger.exception("Token no recibido en creación de pago programado")
        return {"error": "Falta token en cabecera (Authorization o X-Auth-Token)"}, 401
    
    data = data.model_copy(update={"authToken": token})
    
    service = ScheduledPaymentService()

    try:
        new_scheduled_payment = await service.create_new_scheduled_payment(data)
    except AccountNotFoundError:
        return {"error": "La cuenta no existe"}, 404
    except SubscriptionLimitReachedError as e:
        return {"error": f"Límite de pagos programados alcanzado para el plan {e.subscription} (máximo {e.limit})."}, 403
    except Exception as e:
        logger.exception("Error creando pago programado")
        logger.exception(e)
        return {"error": "No se pudo crear el pago programado"}, 503

    if not new_scheduled_payment:
        return {"error": "Ya existe un pago programado con ese id"}, 409
    
    return new_scheduled_payment, 201

@bp.get("/<string:scheduled_payment_id>")
@validate_response(ScheduledPaymentView, 200)
@validate_response(ErrorResponse, 404)
@tag(["v1"])
async def get_scheduled_payment(scheduled_payment_id: str):
    """
    Obtiene un pago programado por su id.

    - 200: Devuelve el pago programado.
    - 404: No existe un pago con ese id.
    """
    
    service = ScheduledPaymentService()
    scheduled_payment = await service.get_scheduled_payment_by_id(scheduled_payment_id)
    
    if not scheduled_payment:
        return {"error": "Pago programado no encontrado"}, 404
    
    return scheduled_payment, 200


@bp.patch("/<string:scheduled_payment_id>")
@validate_request(ScheduledPaymentUpdate)
@validate_response(ScheduledPaymentView, 200)
@validate_response(ErrorResponse, 404)
@tag(["v1"])
async def update_scheduled_payment(scheduled_payment_id: str, data: ScheduledPaymentUpdate):
    """
    Actualiza parcialmente un pago programado.

    - Admite cambios parciales (PATCH).
    - 200: Devuelve el recurso actualizado.
    - 404: No existe el pago.
    """
    
    service = ScheduledPaymentService()
    updated_scheduled_payment = await service.update_scheduled_payment_details(scheduled_payment_id, data)
    
    if not updated_scheduled_payment:
        return {"error": "Pago programado no encontrado"}, 404
    
    return updated_scheduled_payment, 200

@bp.delete("/<string:scheduled_payment_id>")
@validate_response(DeleteResponse, 200)
@validate_response(ErrorResponse, 404)
@tag(["v1"])
async def delete_scheduled_payment(scheduled_payment_id: str):
    """
    Elimina un pago programado.

    - 200: Eliminado correctamente (sin contenido).
    - 404: No existe el pago.
    """
    
    service = ScheduledPaymentService()
    deleted = await service.delete_scheduled_payment(scheduled_payment_id)
    
    if not deleted:
        return {"error": "Pago programado no encontrado"}, 404
    
    return {"status": "deleted", "id": scheduled_payment_id}, 200

@bp.get("/accounts/<string:account_id>")
@validate_response(List[ScheduledPaymentView])
@tag(["v1"])
async def get_scheduled_payments_by_account(account_id: str):
    """
    Lista los pagos programados asociados a una cuenta.

    - 200: Devuelve una lista (posiblemente vacía).
    """
    service = ScheduledPaymentService()
    payments = await service.get_scheduled_payments_by_account_id(account_id)
    return payments, 200

@bp.get("/health")
@validate_response(HealthResponse, 200)
@tag(["v1"])
async def health_check():
    """
    Healthcheck del servicio.

    Pensado para:
    - readiness/liveness en docker/k8s
    - validación rápida en CI

    - 200: El servicio está operativo.
    """

    return {"status": "ok", "service": "scheduled-payments"}, 200

@bp.get("/accounts/<string:account_id>/upcoming")
@validate_response(list[ScheduledPaymentUpcomingView], 200)
@validate_response(ErrorResponse, 400)
@tag(["v1"])
async def get_upcoming_payments(account_id: str):
    """
    Devuelve los próximos pagos estimados para una cuenta.

    Query params:
    - limit (int, opcional): número máximo de resultados (1..100). Por defecto 10.

    Lógica:
    - Calcula la próxima ejecución de cada pago activo.
    - Ordena por fecha más próxima.
    """
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

    return upcoming, 200