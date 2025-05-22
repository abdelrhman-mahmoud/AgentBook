
import re
from pydantic import BaseModel, Field, field_validator


class DateTimeModel(BaseModel):
    date: str = Field(description="Properly formatted date and time", pattern=r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$')

    @field_validator("date")
    def check_format_date(cls, v):
        if not re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$', v):
            raise ValueError("The date should be in format 'YYYY-MM-DD HH:MM'")
        return v

class DateModel(BaseModel):
    date: str = Field(description="Properly formatted date", pattern=r'^\d{4}-\d{2}-\d{2}$')

    @field_validator("date")
    def check_format_date(cls, v):
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            raise ValueError("The date should be in format 'YYYY-MM-DD'")
        return v