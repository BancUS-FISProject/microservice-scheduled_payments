from quart import Quart
from quart import request, jsonify
from .core.rate_limiter import InMemoryFixedWindowRateLimiter
from quart_schema import QuartSchema, Tag

from .core.config import settings
from .core import extensions as ext

from logging import getLogger, Formatter, StreamHandler
from logging.handlers import TimedRotatingFileHandler
from .utils.LoggerColorFormatter import ColorFormatter

from .api.v1.ScheduledPayments_blueprint import bp as scheduled_payments_bp_v1

import asyncio
from .services.ScheduledPayments_service import ScheduledPaymentService

## Logger configuration ##
logger = getLogger()
logger.setLevel(settings.LOG_LEVEL)

console_handler = StreamHandler()
console_handler.setLevel(settings.LOG_LEVEL)
console_format = ColorFormatter(
    "%(levelname)s:     %(message)s"
)
console_handler.setFormatter(console_format)

file_handler = TimedRotatingFileHandler(
    settings.LOG_FILE,
    when="midnight",
    interval=1,
    backupCount=settings.LOG_BACKUP_COUNT
)
file_handler.setLevel(settings.LOG_LEVEL)
file_formatter = Formatter(
    "%(asctime)s - %(levelname)s:     %(message)s"
)
file_handler.setFormatter(file_formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.propagate = False

scheduler_task: asyncio.Task | None = None
rate_limiter: InMemoryFixedWindowRateLimiter | None = None

## Logger configuration ##

def create_app():
    
    app = Quart("Scheduled Payments Service")
    
    # Load settings
    app.config.from_object(settings)
    logger.info("Settings loaded.")
    
    # Load blueprints.
    app.register_blueprint(scheduled_payments_bp_v1)
    logger.info("Routes registered")
    
    # Open API Specification
    schema = QuartSchema()
    schema.tags = [
        Tag(name="v1", description="API version 1"),
    ]
    schema.openapi_path = "/api/openapi.json"
    schema.swagger_ui_path = "/api/docs"
    app.config["QUART_SCHEMA_TITLE"] = "Scheduled Payments Service"
    app.config["QUART_SCHEMA_VERSION"] = "1.0.0"
    app.config["QUART_SCHEMA_DESCRIPTION"] = (
        "Microservicio responsable de gestionar pagos programados.\n\n"
        "Permite:\n"
        "- Crear pagos programados (ONCE/WEEKLY/MONTHLY)\n"
        "- Consultar pagos por id o por cuenta\n"
        "- Consultar próximos pagos (upcoming)\n"
        "- Actualizar y eliminar pagos\n\n"
        "Integra:\n"
        "- Accounts Service: para validar que la cuenta existe y obtener el plan de suscripción\n"
        "- Transfers Service: para ejecutar los pagos cuando llegan a su fecha/hora\n"
    )
    schema.init_app(app)
    # Open API Specification
    
    # Set up everything before serving the service
    @app.before_serving
    async def startup():
        logger.info("Service is starting up...")
        
        # Database
        try:
            await ext.init_db_client()
            
        except Exception as e:
            logger.error("Database connection failed. Shutting down...")
            logger.debug(e)
            raise e
        logger.info("Service started successfully")

        # NTP service
        try:
            await ext.init_ntp_clock()
            
        except Exception as e:
            logger.error("NTP service failed. Shutting down...")
            logger.debug(e)
            raise e
        logger.info("NTP service started successfully")

        # Rate limiter
        global rate_limiter
        if settings.RATE_LIMIT_ENABLED:
            rate_limiter = InMemoryFixedWindowRateLimiter(settings.RATE_LIMIT_WINDOW_SECONDS)
            logger.info(
                "Rate limit enabled (window=%ss)",
                settings.RATE_LIMIT_WINDOW_SECONDS
            )

        global scheduler_task
        service = ScheduledPaymentService()

        async def scheduler_loop():
            logger.info("Scheduler loop started (process_due_payments every 60s)")
            while True:
                try:
                    await service.process_due_payments()
                except Exception as e:
                    logger.error("Scheduler loop error")
                    logger.debug(e)
                interval = settings.SCHEDULER_INTERVAL_SECONDS
                await asyncio.sleep(interval)

        scheduler_task = asyncio.create_task(scheduler_loop())
    
    # Release all resources before shutting down
    @app.after_serving
    async def shutdown():
        logger.info("Service is shutting down...")
        
        ext.close_db_client()
        ext.stop_ntp_clock()

        global scheduler_task
        if scheduler_task:
            scheduler_task.cancel()
            try:
                await scheduler_task
            except asyncio.CancelledError:
                pass
        
        global rate_limiter
        rate_limiter = None
        
        logger.info("Service shut down complete.")

    @app.before_request
    async def apply_rate_limit():

        if not settings.RATE_LIMIT_ENABLED or rate_limiter is None:
            return

        path = request.path or ""
        method = (request.method or "GET").upper()

        limit = settings.RATE_LIMIT_DEFAULT_PER_WINDOW
        key_scope = "ip"  # ip o account

        if method == "POST" and path == "/v1/scheduled-payments/":
            limit = settings.RATE_LIMIT_CREATE_PER_WINDOW
            key_scope = "account"

        elif method == "GET" and path.startswith("/v1/scheduled-payments/accounts/") and "/upcoming" not in path:
            limit = settings.RATE_LIMIT_LIST_PER_WINDOW
            key_scope = "account"

        elif method == "GET" and path.endswith("/upcoming") and path.startswith("/v1/scheduled-payments/accounts/"):
            limit = settings.RATE_LIMIT_UPCOMING_PER_WINDOW
            key_scope = "account"

        elif method == "DELETE" and path.startswith("/v1/scheduled-payments/"):
            limit = settings.RATE_LIMIT_DELETE_PER_WINDOW
            key_scope = "ip"

        account_id: str | None = None

        if key_scope == "account":
            if path.startswith("/v1/scheduled-payments/accounts/"):
                parts = path.split("/")
                if len(parts) >= 5:
                    account_id = parts[4] or None

            if account_id is None and method == "POST" and path == "/v1/scheduled-payments/":
                try:
                    body = await request.get_json(force=False, silent=True) or {}
                    account_id = body.get("accountId")
                except Exception:
                    account_id = None

        ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if not ip:
            ip = request.remote_addr or "unknown"

        if key_scope == "account":
            key = f"acct:{account_id or 'unknown'}:{path}:{method}"
        else:
            key = f"ip:{ip}:{path}:{method}"

        result = await rate_limiter.allow(key=key, limit=limit)

        headers = {
            "X-RateLimit-Limit": str(result.limit),
            "X-RateLimit-Remaining": str(result.remaining),
            "X-RateLimit-Reset": str(result.reset_in_seconds),
        }

        if not result.allowed:
            headers["Retry-After"] = str(result.reset_in_seconds)
            return jsonify({
                "error": "Rate limit excedido",
                "detail": f"Espera {result.reset_in_seconds}s y vuelve a intentarlo."
            }), 429, headers
        
    return app

app = create_app()