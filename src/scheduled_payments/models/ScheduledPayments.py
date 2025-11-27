from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Literal, Union
from datetime import datetime
import uuid

class Beneficiary(BaseModel):
    name: str
    iban: str

class Amount(BaseModel):
    value: float
    currency: str

class MonthlySchedule(BaseModel):
    frequency: Literal["MONTHLY"]
    startDate: datetime
    dayOfMonth: int
    endDate: datetime

class WeeklySchedule(BaseModel):
    type: Literal["WEEKLY"]
    daysOfWeek: List[str]

class OnceSchedule(BaseModel):
    frequency: Literal["ONCE"]
    executionDate: datetime

Schedule = Union[MonthlySchedule, WeeklySchedule, OnceSchedule]

class ScheduledPaymentBase(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    accountId: str
    description: str
    beneficiary: Beneficiary
    amount: Amount
    schedule: Schedule

class ScheduledPaymentCreate(ScheduledPaymentBase):
    pass

class ScheduledPaymentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    accountId: Optional[str] = None
    description: Optional[str] = None
    beneficiary: Optional[Beneficiary] = None
    amount: Optional[Amount] = None
    schedule: Optional[Schedule] = None

class ScheduledPaymentView(ScheduledPaymentBase):
    pass