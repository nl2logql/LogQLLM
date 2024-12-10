from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, field_serializer


class Labels(BaseModel):
    application: str = "hdfs"
    log_level: Optional[str]
    component: Optional[str]


class StructuredMetadata(BaseModel):
    block_id: Optional[str]
    source: Optional[str]
    destination: Optional[str]
    # thread_id: Optional[str]


class LogEntry(BaseModel):
    labels: Labels
    structured_metadata: StructuredMetadata
    timestamp: Optional[datetime] = None
    content: str

    @field_serializer("timestamp")
    def serialize_datetime(self, dt: datetime, _info):
        return dt.isoformat()


class LokiPayload(BaseModel):
    streams: list[Dict[str, Any]]
