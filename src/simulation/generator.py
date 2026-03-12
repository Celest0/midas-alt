"""Public facade for simulation data generation."""

from ..config.settings import MIDASSettings
from .data_generation.install_generator import InstallGenerator
from .generation_result import GenerationResult


class DataGenerator:
    """Facade that coordinates installation-level data generation."""

    def __init__(self, settings: MIDASSettings | None = None, seed: int | None = None):
        """Initialize generation facade with optional settings and seed."""
        self.settings = settings or MIDASSettings.with_defaults()
        self.seed = seed
        self._install_generator = InstallGenerator(settings=self.settings, seed=seed)

    def generate_installation(self) -> GenerationResult:
        """Generate a single installation hierarchy."""
        installation, facilities, systems, work_orders = self._install_generator.generate()
        return GenerationResult.from_single_installation(
            installation=installation,
            facilities=facilities,
            systems=systems,
            work_orders=work_orders,
        )

    def generate_installations(self, count: int) -> GenerationResult:
        """Generate multiple installations and return a merged result."""
        return self._install_generator.generate_by_count(count)
