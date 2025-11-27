from pydantic import BaseModel
from typing import Optional, List

class AccountBase(BaseModel):
    account_id: int
    limit: float
    products: List[str] = []

class AccountCreate(AccountBase):
    pass

class AccountUpdate(BaseModel):
    limit: Optional[float] = None
    products: Optional[List[str]] = None

class AccountView(AccountBase):
    pass