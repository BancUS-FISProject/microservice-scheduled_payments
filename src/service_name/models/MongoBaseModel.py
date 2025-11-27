from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class MongoBaseModel(BaseModel):
    
    id: Optional[str] = Field(alias="_id", default=None)
    
    class Config:
        from_attributes = True
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }