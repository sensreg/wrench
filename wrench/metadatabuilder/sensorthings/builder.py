from datetime import datetime, timezone
from functools import reduce
from operator import __or__
from typing import Sequence

from wrench.harvester.sensorthings.models import Thing
from wrench.metadatabuilder.base import BaseMetadataBuilder
from wrench.metadatabuilder.sensorthings.querybuilder import (
    FilterExpression,
    ThingQuery,
)
from wrench.models import CommonMetadata, Group, TimeFrame
from wrench.utils import ContentGenerator

from .spatial import (
    GeometryCollector,
    PolygonalExtentCalculator,
)


class SensorThingsMetadataBuilder(BaseMetadataBuilder):
    def __init__(
        self,
        base_url: str,
        title: str,
        description: str,
        content_generator: ContentGenerator,
    ):
        """
        Builds metadata for SensorThings API entries.

        Args:
            base_url (str): Base SensorThings URL to harvest items from.
            title (str): Title of the entry in the catalog.
            description (str): Description of the entry in the catalog.
            things (list[Thing]): List of things to extract metadata from.
            content_generator (ContentGenerator): Content generator for generating
                    name and description for device group metadata
        """
        self.base_url = base_url
        self.title = title
        self.description = description
        self.content_generator = content_generator
        self.service_spatial_calculator = PolygonalExtentCalculator()
        self.group_spatial_calculator = GeometryCollector()

    def build_service_metadata(self, things_dict: Sequence[dict]) -> CommonMetadata:
        """
        Retrieves metadata for the SensorThings data.

        This method collects the locations of each 'thing' and calculates the geographic
        extent and timeframe for the data. It then returns a CommonMetadata object
        populated with this information.

        Returns:
            CommonMetadata: An object containing metadata such as endpoint URL, title,
                            identifier, description, spatial extent, temporal extent,
                            source type, and last updated time.
        """
        things = [Thing.model_validate(thing) for thing in things_dict]

        geographic_extent = self.service_spatial_calculator.calculate_extent(things)
        timeframe = self._calculate_timeframe(things)

        self.metadata = CommonMetadata(
            endpoint_url=self.base_url,
            title=self.title,
            identifier=self.title.lower().strip().replace(" ", "_"),
            description=self.description,
            spatial_extent=str(geographic_extent),
            temporal_extent=timeframe,
            source_type="sensorthings",
            last_updated=timeframe.latest_time,
        )

        return self.metadata

    def build_group_metadata(self, group: Group) -> CommonMetadata:
        """
        Groups a list of Things and builds their metadata.

        Args:
            group (Group): The group returned from a Grouper.

        Returns:
            metadata (CommonMetadata): CommonMetadata extracted
            from the groups
        """
        things_in_group = [Thing.model_validate_json(thing) for thing in group.items]

        geographic_extent = self.group_spatial_calculator.calculate_extent(
            things_in_group
        )

        timeframe = self._calculate_timeframe(things_in_group)

        endpoint_url = self._build_group_url(things_in_group)

        content = self.content_generator.generate_group_content(
            group,
            context={
                "service_metadata": self.metadata,
            },
        )

        return CommonMetadata(
            identifier=content.name.lower().strip().replace(" ", "_"),
            title=content.name,
            description=content.description,
            endpoint_url=endpoint_url,
            tags=list(group.parent_classes),
            source_type="sensorthings",
            temporal_extent=timeframe,
            spatial_extent=str(geographic_extent),
            last_updated=timeframe.latest_time,
            thematic_groups=list(group.parent_classes),
        )

    def _calculate_timeframe(self, things: list[Thing]) -> TimeFrame:
        """
        Calculate the overall timeframe spanning all sensor data.

        Args:
            things: List of Thing objects containing datastream information

        Returns:
            TimeFrame: Object containing the earliest start time and latest end time

        Notes:
            - Handles ISO format datetime strings from phenomenon_time
            - All times are converted to UTC timezone
            - Skips datastreams with no phenomenon_time
        """
        # Initialize timeframe boundaries
        time_bounds = {
            "earliest": datetime.max.replace(tzinfo=timezone.utc),
            "latest": datetime.min.replace(tzinfo=timezone.utc),
        }

        # Process each datastream's phenomenon time
        for thing in things:
            for datastream in thing.datastreams:
                if not datastream.phenomenon_time:
                    continue

                # Parse phenomenon time range
                start_str, end_str = datastream.phenomenon_time.split("/")
                timespan = {
                    "start": datetime.fromisoformat(start_str),
                    "end": datetime.fromisoformat(end_str),
                }

                # Update overall boundaries
                time_bounds["earliest"] = min(
                    time_bounds["earliest"], timespan["start"]
                )
                time_bounds["latest"] = max(time_bounds["latest"], timespan["end"])

        return TimeFrame(
            start_time=time_bounds["earliest"], latest_time=time_bounds["latest"]
        )

    def _build_group_url(self, things: list[Thing]) -> str:
        """
        Builds resource URL for groups.

        Takes the ID of each Thing and filters the base URL for Things based on them.

        Args:
            things (list[Thing]): List of things belonging to a group.

        Returns:
            url (str): The resource URL with the ID of Things filtered
        """
        filters: list[FilterExpression] = []

        for thing in things:
            filters.append(ThingQuery.property("@iot.id").eq(thing.id))
        if filters:
            filter_expression = reduce(__or__, filters)
        else:
            raise ValueError("Filters is empty, check if @iot.id exists")

        query = ThingQuery().filter(filter_expression).build()

        return f"{self.base_url}/{query}"
