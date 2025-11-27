from quart import Quart
from quart_schema import QuartSchema, Tag

from .core.config import settings
from .core import extensions as ext

from logging import getLogger, Formatter, StreamHandler
from logging.handlers import TimedRotatingFileHandler
from .utils.LoggerColorFormatter import ColorFormatter

from .api.v1.Accounts_blueprint import bp as accounts_bp_v1

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

## Logger configuration ##

def create_app():
    
    app = Quart("Python Template")
    
    # Load settings
    app.config.from_object(settings)
    logger.info("Settings loaded.")
    
    # Load blueprints.
    app.register_blueprint(accounts_bp_v1)
    logger.info("Routes registered")
    
    # Open API Specification
    schema = QuartSchema()
    schema.tags = [
        Tag(name="v1", description="API version 1"),
    ]
    schema.openapi_path = "/api/openapi.json"
    schema.swagger_ui_path = "/api/docs"
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
    
    # Release all resources before shutting down
    @app.after_serving
    async def shutdown():
        logger.info("Service is shutting down...")
        
        ext.close_db_client()
        
        logger.info("Service shut down complete.")
    
    return app