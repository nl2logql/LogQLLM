from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, field_serializer


class Labels(BaseModel):
    log_file_type: str
    log_level: Optional[str]
    component: Optional[str]
    log_file_name: str
    line_id: int


class StructuredMetadata(BaseModel):
    request_id: Optional[str]
    tenant_id: Optional[str]
    user_id: Optional[str]


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
