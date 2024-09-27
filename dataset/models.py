from enum import Enum
from typing import List
from pydantic import BaseModel, Field


class LineFilterType(str, Enum):
    SINGLE = "single line filter"
    MULTIPLE = "multiple line filters"


class LogStreamFilterType(str, Enum):
    SINGLE = "single log stream selector"
    MULTIPLE = "multiple log stream selectors"


class LogClass(BaseModel):
    chain_of_thought: str = Field(
        ..., description="Steps taken to classify the log query"
    )
    line_filter: LineFilterType
    label_filter: LogStreamFilterType

    # @validator("filter_type")
    # def check_filter_type(cls, v):
    #     if v not in FilterType:
    #         raise ValueError(f"Invalid filter type: {v}")
    #     return v


class MetricType(str, Enum):
    LOG_RANGE = "log_range_aggregation"
    UNWRAPPED_RANGE = "unwrapped_range_aggregation"
    BUILT_IN_RANGE = "built_in_range_aggregation"


class MetricClass(BaseModel):
    chain_of_thought: str = Field(
        ..., description="Steps taken to classify the metric aggregation"
    )

    categories: List[MetricType] | None = Field(
        ...,
        title="Metric Types",
        description="Types of metric aggregation used in combination",
    )

    # class Config:
    #     schema_extra = {
    #         "example": {
    #             "chain_of_thought": "",
    #             "categories": [MetricType.LOG_RANGE, MetricType.UNWRAPPED_RANGE]
    #         }
    #     }
