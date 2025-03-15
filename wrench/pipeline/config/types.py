import enum


class PipelineType(str, enum.Enum):
    """Pipeline type.

    NONE => Pipeline

    SENSOR_PIPELINE ~> SensorPipeline
    """

    NONE = "none"
    SENSOR_PIPELINE = "SensorPipeline"
