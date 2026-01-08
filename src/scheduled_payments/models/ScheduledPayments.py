from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Literal, Union
from datetime import datetime
import uuid

class Beneficiary(BaseModel):
    name: str = Field(..., description="Nombre del beneficiario del pago.")
    iban: str = Field(..., description="IBAN del beneficiario que recibirá la transferencia.")

class Amount(BaseModel):
    value: float = Field(..., gt=0, description="Importe del pago. Debe ser mayor que 0.")
    currency: str = Field(..., description="Divisa del pago (por ejemplo: 'EUR').")

class MonthlySchedule(BaseModel):
    frequency: Literal["MONTHLY"] = Field("MONTHLY", description="Frecuencia mensual.")
    dayOfMonth: int = Field(..., ge=1, le=31, description="Día del mes en el que se ejecuta el pago (1-31).")
    startDate: datetime = Field(..., description="Fecha de inicio del periodo de validez del pago.")
    endDate: datetime = Field(..., description="Fecha de fin del periodo de validez del pago.")

class WeeklySchedule(BaseModel):
    frequency: Literal["WEEKLY"] = Field("WEEKLY", description="Frecuencia semanal.")
    daysOfWeek: List[str] = Field(..., description="Días de la semana en los que se ejecuta el pago (por ejemplo: ['MONDAY','FRIDAY']).")
    startDate: datetime = Field(..., description="Fecha de inicio del periodo de validez del pago.")
    endDate: datetime = Field(..., description="Fecha de fin del periodo de validez del pago.")

class OnceSchedule(BaseModel):
    frequency: Literal["ONCE"] = Field("ONCE", description="Pago de una única ejecución.")
    executionDate: datetime = Field(..., description="Fecha/hora exacta en la que se ejecuta el pago.")

Schedule = Union[MonthlySchedule, WeeklySchedule, OnceSchedule]

class ScheduledPaymentBase(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()),
        description="Identificador único del pago programado (UUID)."
    )
    isActive: bool = Field(True, description="Indica si el pago está activo y puede ejecutarse.")
    lastExecutionAt: Optional[datetime] = Field(
        None,
        description="Marca temporal de la última ejecución (si se ha ejecutado alguna vez)."
    )
    authToken: Optional[str] = Field(
        None,
        description="Token de autorización capturado al crear el pago y reutilizado para ejecutar transferencias."
    )
    accountId: str = Field(..., description="Identificador/IBAN de la cuenta emisora.")
    description: str = Field(..., description="Descripción libre del pago (ej. 'Alquiler', 'Netflix').")
    beneficiary: Beneficiary = Field(..., description="Datos del beneficiario.")
    amount: Amount = Field(..., description="Importe del pago.")
    schedule: Schedule = Field(..., description="Planificación del pago (ONCE/WEEKLY/MONTHLY).")

class ScheduledPaymentCreate(ScheduledPaymentBase):
    """Payload de creación de un pago programado."""
    pass

class ScheduledPaymentUpdate(BaseModel):
    """Payload parcial para modificar un pago existente."""
    model_config = ConfigDict(extra="forbid")
    accountId: Optional[str] = Field(None, description="Nueva cuenta emisora (si aplica).")
    description: Optional[str] = Field(None, description="Nueva descripción del pago.")
    beneficiary: Optional[Beneficiary] = Field(None, description="Nuevo beneficiario.")
    amount: Optional[Amount] = Field(None, description="Nuevo importe.")
    schedule: Optional[Schedule] = Field(None, description="Nueva planificación.")

class ScheduledPaymentView(ScheduledPaymentBase):
    """Vista completa de un pago programado."""
    pass

class ScheduledPaymentUpcomingView(ScheduledPaymentView):
    nextExecutionAt: datetime = Field(..., description="Próxima fecha/hora calculada de ejecución.")