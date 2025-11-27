from ..models.Accounts import AccountCreate, AccountUpdate, AccountView
from ..db.AccountsRepository import AccountRepository
from ..core import extensions as ext


class AccountService:
    def __init__(self, repository: AccountRepository | None = None):
        self.repo = repository or AccountRepository(ext.db)
    
    async def create_new_account(self, data: AccountCreate) -> AccountView:
        # Business logic here
  
        new_account_doc = await self.repo.insert_account(data)
        
        return new_account_doc
    
    async def get_account_by_id(self, account_id: str) -> AccountView | None:
        return await self.repo.find_account_by_id(account_id)
    
    async def update_account_details(self, account_id: str, data: AccountUpdate) -> AccountView | None:
        return await self.repo.update_account(account_id, data)