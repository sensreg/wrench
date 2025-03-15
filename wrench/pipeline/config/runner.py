from typing import Any

from wrench.pipeline.config.config_reader import ConfigReader
from wrench.pipeline.config.pipeline_config import AbstractPipelineConfig
from wrench.pipeline.pipeline import Pipeline

from .pipeline_config import PipelineConfig


class PipelineRunner:
    """Runner to execute pipelines from different sources."""

    def __init__(self, pipeline_definition, config=None):
        """Initializes a pipeline runner."""
        self.pipeline = Pipeline.from_definition(pipeline_definition)
        self.config = config

    @classmethod
    def from_config(cls, config: AbstractPipelineConfig):
        """Create a runner from configuration."""
        pipeline_definition = config.parse()
        return cls(pipeline_definition, config=config)

    @classmethod
    def from_config_file(cls, file_path):
        """Create a runner from a configuration file."""
        # Read and parse config file
        data = ConfigReader().read(file_path)
        config = PipelineConfig.model_validate(data)
        return cls.from_config(config)

    async def run(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """Run the pipeline with the given input."""
        # Merge config parameters with user input
        # Call pipeline.run() with the merged parameters
        return await self.pipeline.run(user_input)
