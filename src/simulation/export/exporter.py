"""Main exporter class for simulated data."""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ...models import Facility, Installation, System
from ...models.work_order import WorkOrder
from .config import ExportConfig
from .enums import OutputFormat, OutputLayout
from .formatters import CSVFormatter, ExcelFormatter
from .transformers import DataTransformer

if TYPE_CHECKING:
    from ...config import MIDASSettings


class DataExporter:
    """Handles generation and export of simulated data to various file formats.

    This is the main interface for generating and exporting simulated data.
    """

    def __init__(
        self,
        file_name: str,
        output_format: OutputFormat | str,
        output_directory: str | Path = ".",
        include_time_series: bool = False,
        layout: OutputLayout | str = OutputLayout.NORMALIZED,
        generate_metadata: bool = True,
        description: str = "",
        settings: "MIDASSettings | None" = None,
    ) -> None:
        """Initialize the data exporter.

        Args:
            file_name: Base name for the output file (without extension).
            output_format: Format for export (csv, xlsx).
            output_directory: Directory where file will be saved.
            include_time_series: Whether to include time series data.
            layout: Output layout - normalized or denormalized.
            generate_metadata: Whether to generate a metadata JSON file.
            description: Optional description for the dataset.
            settings: Application settings for reference data.

        """
        # Lazy imports to avoid circular dependency
        from ...config import MIDASSettings
        from ..generator import DataGenerator

        self.settings = settings or MIDASSettings.with_defaults()

        # Create export configuration
        self.config = ExportConfig(
            file_name=file_name,
            output_format=output_format,
            output_directory=output_directory,
            include_time_series=include_time_series,
            layout=layout,
            generate_metadata=generate_metadata,
            description=description,
        )

        # Initialize components
        self.generator = DataGenerator(settings=self.settings)
        self.transformer = DataTransformer(
            settings=self.settings,
            include_time_series=include_time_series,
        )

        # Create formatter based on output format
        self.formatter = self._create_formatter()

    def _create_formatter(self):
        """Create the appropriate formatter based on output format."""
        if self.config.output_format == OutputFormat.CSV:
            return CSVFormatter(self.config, self.transformer)
        elif self.config.output_format == OutputFormat.XLSX:
            return ExcelFormatter(self.config, self.transformer)
        else:
            raise ValueError(f"Invalid output format: expected one of ['csv', 'xlsx'] (got {self.config.output_format})")

    @property
    def file_path(self) -> Path:
        """Get the full file path for the output file."""
        return self.config.file_path

    @property
    def metadata_path(self) -> Path:
        """Get the path for the metadata file."""
        return self.config.metadata_path

    def generate_and_export(
        self,
        method: str = "default",
        target_count: int | None = None,
    ) -> Path:
        """Generate simulated data and export to file.

        Args:
            method: Generation method - "default", "installations", or "facilities".
            target_count: Number of items to generate (required for installations/facilities).

        Returns:
            Path to the created file.

        """
        # Generate data
        if method == "installations":
            if target_count is None:
                raise ValueError("Invalid argument: target_count is required for method 'installations' (got None)")
            result = self.generator.generate_installations(target_count)

        elif method == "facilities":
            if target_count is None:
                raise ValueError("Invalid argument: target_count is required for method 'facilities' (got None)")
            result = self.generator.generate_installation()
            installations = list(result.installations)
            facilities = list(result.facilities)
            systems = list(result.systems)
            work_orders = list(result.work_orders)
            # Generate additional facilities
            for _ in range(target_count - len(facilities)):
                extra = self.generator.generate_installation()
                facilities.extend(extra.facilities)
                systems.extend(extra.systems)
                work_orders.extend(extra.work_orders)
                installations.extend(extra.installations)
            result.installations = installations
            result.facilities = facilities
            result.systems = systems
            result.work_orders = work_orders

        else:  # default
            result = self.generator.generate_installation()

        installations = result.installations
        facilities = result.facilities
        systems = result.systems
        work_orders = result.work_orders
        # Create metadata
        metadata = self._create_metadata(method, target_count, installations, facilities, systems, work_orders)

        # Export using formatter
        return self.formatter.export(installations, facilities, systems, work_orders, metadata)

    def export_existing(
        self,
        installations: list[Installation],
        facilities: list[Facility],
        systems: list[System],
        work_orders: list[WorkOrder],
    ) -> Path:
        """Export existing data (not generated).

        Args:
            installations: List of installations to export.
            facilities: List of facilities to export.
            systems: List of systems to export.
            work_orders: List of work orders to export.

        Returns:
            Path to the created file.

        """
        metadata = self._create_metadata("existing", None, installations, facilities, systems, work_orders)
        return self.formatter.export(installations, facilities, systems, work_orders, metadata)

    def _create_metadata(
        self,
        method: str,
        target_count: int | None,
        installations: list[Installation],
        facilities: list[Facility],
        systems: list[System],
        work_orders: list[WorkOrder],
    ) -> dict:
        """Create metadata dictionary."""
        return {
            "generated_at": datetime.now().isoformat(),
            "description": self.config.description,
            "generation_method": method,
            "target_count": target_count,
            "output_format": self.config.output_format.value,
            "layout": self.config.layout.value,
            "include_time_series": self.config.include_time_series,
            "counts": {
                "installations": len(installations),
                "facilities": len(facilities),
                "systems": len(systems),
                "work_orders": len(work_orders),
            },
        }
