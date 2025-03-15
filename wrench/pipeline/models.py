import datetime
from collections import defaultdict
from enum import Enum
from typing import Any, Awaitable, Protocol, Union

from pydantic import BaseModel, ConfigDict, Field

from wrench.pipeline.component import Component, DataModel


class ComponentDefinition(BaseModel):
    """Definition of a pipeline component."""

    name: str
    component: Component
    run_params: dict[str, Any] = {}

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ConnectionDefinition(BaseModel):
    """Definition of a connection between pipeline components."""

    start: str
    end: str
    input_config: dict[str, str]


class PipelineDefinition(BaseModel):
    """Definition of a pipeline with components and connections."""

    components: list[ComponentDefinition]
    connections: list[ConnectionDefinition]

    def get_run_params(self) -> defaultdict[str, dict[str, Any]]:
        return defaultdict(
            dict, {c.name: c.run_params for c in self.components if c.run_params}
        )


class RunStatus(Enum):
    """Status of a pipeline component run."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"

    def possible_next_status(self) -> list["RunStatus"]:
        """Get possible next statuses from current."""
        if self == RunStatus.PENDING:
            return [RunStatus.RUNNING]
        if self == RunStatus.RUNNING:
            return [RunStatus.DONE, RunStatus.FAILED]
        # terminal states cannot transition
        return []


class RunResult(BaseModel):
    """Result of a pipeline component run."""

    status: RunStatus = RunStatus.DONE
    result: DataModel | None = None
    timestamp: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    error: Exception | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class EventType(Enum):
    PIPELINE_STARTED = "PIPELINE_STARTED"
    TASK_STARTED = "TASK_STARTED"
    TASK_FINISHED = "TASK_FINISHED"
    PIPELINE_FINISHED = "PIPELINE_FINISHED"

    @property
    def is_pipeline_event(self) -> bool:
        return self in [EventType.PIPELINE_STARTED, EventType.PIPELINE_FINISHED]

    @property
    def is_task_event(self) -> bool:
        return self in [EventType.TASK_STARTED, EventType.TASK_FINISHED]


class Event(BaseModel):
    event_type: EventType
    run_id: str
    """Pipeline unique run_id, same as the one returned in PipelineResult after pipeline.run"""
    timestamp: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    message: str | None = None
    """Optional information about the status"""
    payload: dict[str, Any] | None = None
    """Input or output data depending on the type of event"""


class PipelineEvent(Event):
    pass


class TaskEvent(Event):
    task_name: str
    """Name of the task as defined in pipeline.add_component"""


class EventCallbackProtocol(Protocol):
    def __call__(self, event: Event) -> Awaitable[None]: ...


EntityInputType = Union[str, dict[str, Union[str, list[dict[str, str]]]]]
RelationInputType = Union[str, dict[str, Union[str, list[dict[str, str]]]]]
"""Types derived from the SchemaEntity and SchemaRelation types,
 so the possible types for dict values are:
- str (for label and description)
- list[dict[str, str]] (for properties)
"""
