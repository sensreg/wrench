class PipelineError(Exception):
    """Base exception for all Pipeline related errors."""

    pass


class PipelineDefinitionError(PipelineError):
    """Raised when pipeline definition is invalid."""

    pass


class ComponentNotFoundError(PipelineError):
    """Raised when a referenced component is not found."""


class ComponentExecutionError(PipelineError):
    """Raised when a component fails during execution."""

    pass


class ValidationError(PipelineError):
    """Raised when validation of pipeline connections fails."""

    pass


class CyclicPipelineError(PipelineError):
    """Raised when a cycle is detected in the pipeline graph."""

    pass


class PipelineStatusUpdateError(Exception):
    """Raises when trying an invalid change of state (e.g. DONE => DOING)."""

    pass


class InvalidJSONError(Exception):
    """Raised when JSON repair fails to produce valid JSON."""

    pass


class MissingDependencyError(PipelineError):
    """Raised when a component's dependencies are not satisfied."""

    pass
