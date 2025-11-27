from ..models.Accounts import AccountCreate, AccountUpdate, AccountView

class AccountRepository:
    """
    
    """
    def __init__(self, db):
        self.collection = db["accounts"]
    
    async def insert_account(self, data: AccountCreate) -> AccountView:
        account_doc = data.model_dump(by_alias=True)
        
        result = await self.collection.insert_one(account_doc)
        created_doc = await self.collection.find_one({"_id": result.inserted_id})
        
        created_doc["_id"] = str(created_doc["_id"])
        
        return AccountView.model_validate(created_doc)
    
    async def find_account_by_id(self, account_id: str) -> AccountView | None:
        doc = await self.collection.find_one({"account_id": int(account_id)})
        
        if doc:
            doc["_id"] = str(doc["_id"])
            return AccountView.model_validate(doc)
        return None
    
    async def update_account(self, account_id: str, data: AccountUpdate) -> AccountView | None:
        update_data = data.model_dump(exclude_unset=True)
        
        if not update_data:
            return await self.find_account_by_id(account_id)
        
        await self.collection.update_one(
            {"account_id": int(account_id)},
            {"$set": update_data}
            )
        
        return await self.find_account_by_id(account_id)