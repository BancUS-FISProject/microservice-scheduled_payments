from quart import Blueprint
from quart_schema import validate_request, validate_response, tag
from ...models.Accounts import AccountCreate, AccountUpdate, AccountView
from ...services.Accounts_service import AccountService

from logging import getLogger
from ...core.config import settings

logger = getLogger(__name__)
logger.setLevel(settings.LOG_LEVEL)

bp = Blueprint("accounts_v1", __name__, url_prefix="/v1/accounts")

@bp.post("/")
@validate_request(AccountCreate)
@validate_response(AccountView, 201)
@tag(["v1"])
async def create_account(data: AccountCreate):

    service = AccountService()
    new_account = await service.create_new_account(data)
    
    return new_account

@bp.get("/<string:account_id>")
@validate_response(AccountView)
@tag(["v1"])
async def get_account(account_id: str):
    
    service = AccountService()
    account = await service.get_account_by_id(account_id)
    
    if not account:
        return {"error": "Cuenta no encontrada"}, 404
    
    return account


@bp.patch("/<string:account_id>")
@validate_request(AccountUpdate)
@validate_response(AccountView)
@tag(["v1"])
async def update_account(account_id: str, data: AccountUpdate):
    
    service = AccountService()
    updated_account = await service.update_account_details(account_id, data)
    
    if not updated_account:
        return {"error": "Cuenta no encontrada"}, 404
    
    return updated_account