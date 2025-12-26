from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .config import settings
from .ntp_clock import NtpClock

from logging import getLogger

logger = getLogger(__name__)
logger.setLevel(settings.LOG_LEVEL)

db_client: AsyncIOMotorClient | None = None
db: AsyncIOMotorDatabase | None = None

ntp_clock: NtpClock | None = None

async def init_db_client():
    global db_client, db
    logger.info(f"Connecting to Database")
    try:
        db_client = AsyncIOMotorClient(
            settings.MONGO_CONNECTION_STRING,
            maxPoolSize=100,
            minPoolSize=10,
            timeoutMS=5000
            )
        await db_client.admin.command('ping')
        
        db = db_client[settings.MONGO_DATABASE_NAME]
        
        logger.info("Database connected")
    
    except Exception as e:
        logger.error("Error connecting to database")
        logger.debug(e)
        raise e
    
def close_db_client():
    global db_client, db
    logger.info(f"Closing Database")
    try:
        db_client.close()
    except Exception as e:
        logger.error("Error closing database")
        logger.debug(e)

async def init_ntp_clock():
    global ntp_clock
    if ntp_clock is not None:
        return
    ntp_clock = NtpClock(
        server=settings.NTP_SERVER,
        refresh_seconds=settings.NTP_REFRESH_SECONDS,
        timeout=settings.NTP_TIMEOUT_SECONDS,
    )
    logger.info("NTP clock listo (server=%s offset=%.6fs)",
                settings.NTP_SERVER, ntp_clock.offset_seconds())

def stop_ntp_clock():
    global ntp_clock
    if ntp_clock is None:
        return
    ntp_clock.stop()
    ntp_clock = None