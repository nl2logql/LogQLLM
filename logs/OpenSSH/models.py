from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, field_serializer, field_validator


class Labels(BaseModel):
    application: str = "openssh"
    hostname: str = "LabSZ"


class StructuredMetadata(BaseModel):
    process_id: str
    rhost: Optional[str] = None
    ruser: Optional[str] = None

    @field_validator("process_id", mode="before")
    @classmethod
    def convert_process_id_to_str(cls, v):
        return str(v) if isinstance(v, int) else v


class LogEntry(BaseModel):
    labels: Labels
    structured_metadata: StructuredMetadata
    timestamp: datetime
    content: str

    @field_serializer("timestamp")
    def serialize_datetime(self, dt: datetime, _info):
        return dt.isoformat()


class LokiPayload(BaseModel):
    streams: list[Dict[str, Any]]
