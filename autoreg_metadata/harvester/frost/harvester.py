from .config import FrostConfig
from typing import Optional
from pathlib import Path
import yaml
from datetime import datetime, timezone
from typing import Callable, TypeVar
import requests
import time


from autoreg_metadata.log import logger
from autoreg_metadata.common.models import Coordinate, CommonMetadata, TimeFrame
from autoreg_metadata.harvester.base import BaseHarvester

from .models import FrostBase, GenericLocation, Location, Thing
from .translator import FrostTranslationService


# Type definitions
T = TypeVar('T', bound=FrostBase)
ProcessingFn = Callable[[list[T]], list[T]]
HarvesterOption = Callable[['FrostHarvester'], None]


class FrostHarvester(BaseHarvester):
    """
    A class to interact with the FROST server and retrieve SensorThings API Entities.
    """

    def __init__(
        self,
        config: FrostConfig | str | Path,
        *options: HarvesterOption,
        location_model: type[GenericLocation] = Location,
    ):
        # Load config if path is provided
        if isinstance(config, (str, Path)):
            with open(config, 'r') as f:
                config_dict = yaml.safe_load(f)
                config = FrostConfig.model_validate(config_dict)

        self.config = config
        self.logger = logger.getChild(self.__class__.__name__)

        # Set up translator if configured
        translator_config = self.config.translator
        self.translator = FrostTranslationService(
            translator_config.url, translator_config.source_lang) if translator_config else None

        self.location_model = location_model

        # Apply any runtime options that might override config
        for option in options:
            option(self)

    def enrich(self, limit: Optional[int] = None) -> tuple[CommonMetadata, list[Thing]]:
        """
        Enriches the metadata by fetching things and locations, and calculating the geographic extent and timeframe.
        Args:
            limit (Optional[int]): The maximum number of items to fetch. If None, the default limit from the config of -1 (no limit) is used.
        Returns:
            tuple[EndpointMetadata, list[Thing]]: A tuple containing the enriched endpoint metadata and a list of fetched things.
        """

        # Use provided limit or fall back to config default
        fetch_limit = limit if limit is not None else self.config.default_limit

        things = self.fetch_things(limit=fetch_limit)
        locations = self.fetch_locations(limit=fetch_limit)

        geographic_extent = self._calculate_geographic_extent(locations)
        timeframe = self._calculate_timeframe(things)

        return (
            CommonMetadata(
                endpoint_url=self.config.base_url,
                title=self.config.title,
                identifier=self.config.identifier,
                description=self.config.description,
                spatial_extent=geographic_extent,
                temporal_extent=timeframe,
                source_type='frost',
                last_updated=timeframe.latest_time,
            ),
            things
        )

    def fetch_things(self, limit: int = -1) -> list[Thing]:
        """Fetch Things with their associated Datastreams and Sensors"""
        things = self._fetch_paginated(
            "Things?$expand=Datastreams($expand=Sensor)",
            Thing,
            limit=limit,
        )

        if not self.translator:
            return things

        # Do translation if translator exists
        translated_things = []
        for thing in things:
            try:
                translated_thing = self.translator.translate(thing)
                translated_things.append(translated_thing)
            except Exception as e:
                self.logger.error(
                    "Translation failed for thing %s: %s", thing.id, e)
                translated_things.append(thing)

        return translated_things

    def fetch_locations(self, limit: int = -1) -> list[GenericLocation]:
        """Fetch Locations for further processing"""
        return self._fetch_paginated(
            "Locations",
            self.location_model,
            limit=limit
        )

    def _fetch_paginated[T](self, endpoint: str, model_class: type[T], limit: int = -1) -> list[T]:
        """Generic paginated data fetching"""
        url = f"{self.config.base_url}/{endpoint}"
        page_count = 1
        items: list[T] = []

        while url:
            self.logger.info("Fetching page %s", page_count)
            try:
                response = requests.get(
                    url, timeout=self.config.pagination.timeout)
                response.raise_for_status()
                data = response.json()

                if "value" not in data:
                    break

                for value in data["value"]:
                    if limit != -1 and len(items) >= limit:
                        return items

                    item = model_class.model_validate(value)
                    items.append(item)

                page_count += 1
                self.logger.info("Added %d items from page %d",
                                 len(data["value"]), page_count)

                url = data.get("@iot.nextLink")
                if url:
                    time.sleep(self.config.pagination.page_delay)

            except requests.RequestException as e:
                logger.error("Error fetching data: %s", e)
                break

        return items

    def _calculate_geographic_extent(self, locations: list[GenericLocation]) -> list[Coordinate]:
        """Calculate the geographic bounding box from locations"""
        min_lat = float('inf')
        max_lat = float('-inf')
        min_lng = float('inf')
        max_lng = float('-inf')

        for loc in locations:
            lng, lat = loc.get_coordinates()
            min_lat = min(min_lat, lat)
            max_lat = max(max_lat, lat)
            min_lng = min(min_lng, lng)
            max_lng = max(max_lng, lng)

        return [
            Coordinate(longitude=min_lng, latitude=min_lat),
            Coordinate(longitude=min_lng, latitude=max_lat),
            Coordinate(longitude=max_lng, latitude=max_lat),
            Coordinate(longitude=max_lng, latitude=min_lat),
            Coordinate(longitude=min_lng, latitude=min_lat)
        ]

    def _calculate_timeframe(self, things: list[Thing]) -> TimeFrame:
        """Calculate the overall timeframe from thing data"""
        earliest = datetime.max.replace(tzinfo=timezone.utc)
        latest = datetime.min.replace(tzinfo=timezone.utc)

        for thing in things:
            for ds in thing.datastreams:
                if ds.phenomenon_time:
                    start, end = ds.phenomenon_time.split('/')
                    start_time = datetime.fromisoformat(start)
                    end_time = datetime.fromisoformat(end)
                    earliest = min(earliest, start_time)
                    latest = max(latest, end_time)

        return TimeFrame(start_time=earliest, latest_time=latest)
