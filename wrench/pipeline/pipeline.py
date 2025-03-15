import asyncio
import uuid
from typing import Any, Optional

from wrench.log import logger

from .component import Component, DataModel
from .exceptions import (
    ComponentNotFoundError,
    PipelineDefinitionError,
    PipelineStatusUpdateError,
    ValidationError,
)
from .models import (
    PipelineDefinition,
    RunResult,
    RunStatus,
)
from .pipeline_graph import PipelineEdge, PipelineGraph, PipelineNode, PipelineResult
from .stores import InMemoryStore, ResultStore


class TaskNode(PipelineNode):
    """Node representing a runnable component in the pipeline graph."""

    def __init__(self, name: str, component: Component):
        """
        Initializes a node component in the pipeline graph.

        Args:
            name (str): Name of the node.
            component (Component): Component to be contained in the node.
        """
        super().__init__(name)
        self.component = component
        self.logger = logger.getChild(self.__class__.__name__)

    async def run(self, **inputs: Any) -> RunResult:
        """Execute the component with the given inputs."""
        try:
            result = await self.component.run(**inputs)
            return RunResult(status=RunStatus.DONE, result=result)
        except Exception as e:
            self.logger.exception(f"Error executing component {self.name}: {str(e)}")
            return RunResult(status=RunStatus.FAILED, error=e)


class Pipeline(PipelineGraph[TaskNode, PipelineEdge]):
    """
    Pipeline implementation with component validation and execution.

    Features:
    - Component graph with validation
    - Type validation between connected components
    - Status tracking
    - Result storage
    """

    def __init__(self, store: Optional[ResultStore] = None):
        """
        Initializes a Pipeline with given store.

        Args:
            store (Optional[ResultStore]) : Store to be used to store pipeline results.
        """
        super().__init__()
        self.store = store or InMemoryStore()  # default store
        self.final_results = InMemoryStore()  # For storing leaf node results
        self.is_validated = False
        self.param_mapping: dict[str, dict[str, dict[str, str]]] = {}
        self.missing_inputs: dict[str, list[str]] = {}

        self.logger = logger.getChild(self.__class__.__name__)

    def add_component(self, name: str, component: Component) -> None:
        """Add a component to the pipeline."""
        if not isinstance(component, Component):
            raise TypeError(
                f"Component must be an instance of Component, got {type(component)}"
            )

        node = TaskNode(name, component)
        self.add_node(node)
        self.is_validated = False

    def set_component(self, name: str, component: Component) -> None:
        """Replace an existing component with a new one."""
        if not isinstance(component, Component):
            raise TypeError(
                f"Component must be an instance of Component, got {type(component)}"
            )

        node = TaskNode(name, component)
        self.set_node(node)
        self.is_validated = False

    def connect(
        self,
        start_component: str,
        end_component: str,
        input_config: dict[str, str] | None = None,
    ) -> None:
        """
        Connect components in the pipeline.

        Args:
            start_component (str): Name of the source component
            end_component (str): Name of the target component
            input_config (dict[str,str] | None): Mapping of target inputs
                to source outputs
        """
        if start_component not in self._nodes:
            raise ComponentNotFoundError(f"Component '{start_component}' not found")
        if end_component not in self._nodes:
            raise ComponentNotFoundError(f"Component '{end_component}' not found")

        edge = PipelineEdge(
            start_component, end_component, {"input_config": input_config or {}}
        )

        try:
            self.add_edge(edge)
        except ValueError as e:
            raise PipelineDefinitionError(str(e))

        self.is_validated = False

    @classmethod
    def from_definition(
        cls, definition: PipelineDefinition, store: ResultStore | None = None
    ) -> "Pipeline":
        """Create a pipeline from a PipelineDefinition."""
        pipeline = cls(store=store)

        # Add all components
        for comp_def in definition.components:
            pipeline.add_component(comp_def.name, comp_def.component)

        # Add all connections
        for conn in definition.connections:
            pipeline.connect(conn.start, conn.end, conn.input_config)

        return pipeline

    def validate(self) -> None:
        """
        Validate the entire pipeline.

        Checks:
        - No cycles in the graph
        - All required inputs are provided
        - Input and output types are compatible
        """
        if self.is_validated:
            return

        # Check for cycles
        if self.is_cyclic():
            raise PipelineDefinitionError("Pipeline contains cycles")

        # Validate each component's connections
        for node in self._nodes.values():
            self._validate_component_connections(node)

        self.is_validated = True

    def _validate_component_connections(self, node: TaskNode) -> None:
        """
        Validate connections for a single component.

        Checks if outputs from previous nodes have fulfill
        all required inputs of the current node.
        """
        component = node.component
        required_inputs = {
            name: info
            for name, info in component.component_inputs.items()
            if not info["has_default"]
        }

        # Get inputs from connections
        provided_inputs: set[str] = set()
        prev_edges = self.previous_edges(node.name)

        component_mapping: dict[str, Any] = {}

        for edge in prev_edges:
            inputs, components = self._validate_input_mapping(node, component, edge)

            provided_inputs = provided_inputs | inputs
            component_mapping = component_mapping | components

        # Store the mapping for this component
        self.param_mapping[node.name] = component_mapping

        # Check for missing required inputs
        missing = set(required_inputs.keys()) - provided_inputs
        self.missing_inputs[node.name] = list(missing)

    def _validate_input_mapping(
        self,
        node: TaskNode,
        component: Component,
        edge: PipelineEdge,
    ) -> tuple[set, dict]:
        provided_inputs: set[str] = set()
        component_mapping: dict[str, Any] = {}

        input_config: dict[str, str] = edge.data.get("input_config", {})

        for target_param, source_path in input_config.items():
            # Check target parameter exists
            if target_param not in component.component_inputs:
                raise ValidationError(
                    f"Parameter '{target_param}' is not a valid input for component '{node.name}'"
                )

            # Check if already mapped
            if target_param in component_mapping:
                raise ValidationError(
                    f"Parameter '{target_param}' is already mapped for '{node.name}'"
                )

            # Handle dot notation for output fields
            if "." in source_path:
                source_component, output_field = source_path.split(".", 1)

                # Check source component exists
                if source_component not in self._nodes:
                    raise ValidationError(
                        f"Source component '{source_component}' does not exist"
                    )

                    # Check output field exists in source component
                source_node = self._nodes[source_component]
                if output_field not in source_node.component.component_outputs:
                    raise ValidationError(
                        f"Output field '{output_field}' does not exist in component '{source_component}'"
                    )

                    # Check types are compatible
                source_type = source_node.component.component_outputs[output_field][
                    "annotation"
                ]
                target_type = component.component_inputs[target_param]["annotation"]

                if not self._check_type_compatibility(source_type, target_type):  # type: ignore
                    raise ValidationError(
                        f"Type mismatch: {source_component}.{output_field} ({source_type}) is not compatible with "
                        f"{node.name}.{target_param} ({target_type})"
                    )

                component_mapping[target_param] = {
                    "component": source_component,
                    "param": output_field,
                }
            else:
                # Whole component result mapping
                source_component = source_path

                # Check source component exists
                if source_component not in self._nodes:
                    raise ValidationError(
                        f"Source component '{source_component}' does not exist"
                    )

                component_mapping[target_param] = {"component": source_component}

            provided_inputs.add(target_param)

        return provided_inputs, component_mapping

    def _check_type_compatibility(self, source_type: type, target_type: type) -> bool:
        """Check if the source type is compatible with the target type."""
        # For now, use simple issubclass check
        # This could be enhanced with more sophisticated type checking
        try:
            return issubclass(source_type, target_type)
        except TypeError:
            # Handle complex types
            return True

    def validate_run_inputs(self, inputs: dict[str, Any]) -> None:
        """Validate that all missing required inputs are provided in the run inputs."""
        if not self.is_validated:
            self.validate()

        for component_name, missing in self.missing_inputs.items():
            component_inputs = inputs.get(component_name, {})
            for param in missing:
                if param not in component_inputs:
                    raise ValidationError(
                        f"Required parameter '{param}' for component '{component_name}' not provided"
                    )

    async def run(self, inputs: dict[str, Any] | None = None) -> PipelineResult:
        """
        Execute the pipeline.

        Args:
            inputs: Input data for components

        Returns:
            dict containing results from leaf components
        """
        inputs = inputs or {}

        # Validate pipeline and inputs
        self.validate()
        self.validate_run_inputs(inputs)

        # Generate run ID
        run_id = str(uuid.uuid4())
        self.logger.info(f"Starting pipeline run {run_id}")

        # Initialize component statuses
        for node in self._nodes.values():
            await self.store.add_status_for_component(
                run_id, node.name, RunStatus.PENDING.value
            )

        # Start from root nodes
        root_nodes = self.roots()
        await asyncio.gather(
            *[self._execute_node(run_id, node.name, inputs) for node in root_nodes]
        )

        # Collect results from leaf nodes
        final_results = {}
        for node in self.leaves():
            result = await self.store.get_result_for_component(run_id, node.name)
            if result:
                final_results[node.name] = result

        # Store and return final results
        await self.final_results.add(run_id, final_results)
        return PipelineResult(run_id=run_id, results=final_results)

    async def get_node_status(self, run_id: str, node_name: str) -> RunStatus:
        """Get the current status of a node in a specific run."""
        status_str = await self.store.get_status_for_component(run_id, node_name)
        return RunStatus(status_str) if status_str else RunStatus.PENDING

    async def set_node_status(
        self, run_id: str, node_name: str, status: RunStatus
    ) -> None:
        """Set the status of a node in a specific run."""
        current_status = await self.get_node_status(run_id, node_name)

        # Check if the status transition is valid
        if status not in current_status.possible_next_status():
            raise PipelineStatusUpdateError(
                f"Invalid status transition: {current_status} -> {status}"
            )

        await self.store.add_status_for_component(run_id, node_name, status.value)

    async def _execute_node(
        self, run_id: str, node_name: str, global_inputs: dict[str, Any]
    ) -> None:
        """Execute a single node in the pipeline."""
        # Check if all dependencies are complete
        for edge in self.previous_edges(node_name):
            dep_status = await self.get_node_status(run_id, edge.start)
            if dep_status != RunStatus.DONE:
                # Dependency not ready yet
                return

        # Set status to running
        try:
            await self.set_node_status(run_id, node_name, RunStatus.RUNNING)
        except PipelineStatusUpdateError:
            # Another instance is already running this node
            return

        node = self._nodes[node_name]
        self.logger.info(f"Executing node {node_name}")

        try:
            # Prepare inputs
            node_inputs = await self._prepare_node_inputs(
                run_id, node_name, global_inputs
            )

            # Run the component
            run_result = await node.run(**node_inputs)

            # Store results
            if run_result.result is not None:
                if isinstance(run_result.result, DataModel):
                    await self.store.add_result_for_component(
                        run_id, node_name, run_result.result.model_dump()
                    )
                else:
                    await self.store.add_result_for_component(
                        run_id, node_name, run_result.result
                    )

            # Update status
            await self.set_node_status(run_id, node_name, run_result.status)

            # If successful, schedule child nodes
            if run_result.status == RunStatus.DONE:
                # Schedule all children
                for edge in self.next_edges(node_name):
                    asyncio.create_task(
                        self._execute_node(run_id, edge.end, global_inputs)
                    )
            else:
                self.logger.warning(
                    f"Node {node_name} completed with status {run_result.status}"
                )

        except Exception as e:
            self.logger.exception(f"Error executing node {node_name}: {str(e)}")
            await self.set_node_status(run_id, node_name, RunStatus.FAILED)
            # Store error information
            await self.store.add_result_for_component(
                run_id, node_name, {"error": str(e)}
            )

    async def _prepare_node_inputs(
        self, run_id: str, node_name: str, global_inputs: dict[str, Any]
    ) -> dict[str, Any]:
        """Prepare inputs for a node execution."""
        node_inputs = {}

        # Add component-specific inputs from global inputs
        if node_name in global_inputs:
            node_inputs.update(global_inputs[node_name])

        # Add inputs from parent nodes
        node_mapping = self.param_mapping.get(node_name, {})
        for param_name, mapping in node_mapping.items():
            source_component = mapping["component"]
            source_param = mapping.get("param")

            # Get the source component result
            source_result = await self.store.get_result_for_component(
                run_id, source_component
            )

            if source_result is None:
                continue

            if source_param:
                # Map specific field
                if source_param in source_result:
                    node_inputs[param_name] = source_result[source_param]
            else:
                # Map entire result
                node_inputs[param_name] = source_result

        return node_inputs
