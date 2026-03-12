"""Factory functions for creating menu handlers."""

from rich.console import Console

from src.cli.handlers.config_handlers import (
    handle_reload_configuration,
    handle_view_config_values,
    handle_view_facility_types_summary,
    handle_view_installation_locations_summary,
    handle_view_system_types_summary,
)
from src.cli.handlers.simulate_handlers import (
    handle_generate_data,
    handle_quick_generate,
    handle_view_facility_and_system,
    handle_view_simulated_data_examples,
)
from src.cli.menu.menu_builder import MenuBuilder

console = Console()


def get_configuration_menu():
    """Create and return the configuration menu."""
    builder = MenuBuilder("Configuration Menu")
    builder.add_item(
        "View Facility Types Summary",
        handle_view_facility_types_summary,
        description="Display a summary of all facility types loaded from the configuration file",
    )
    builder.add_item(
        "View System Types Summary",
        handle_view_system_types_summary,
        description="Display a summary of all system types loaded from the configuration file",
    )
    builder.add_item(
        "View Installation Locations Summary",
        handle_view_installation_locations_summary,
        description="Display a summary of all installation locations loaded from the configuration file",
    )
    builder.add_item(
        "View Config Values",
        handle_view_config_values,
        description="View all current configuration values used by the MIDAS application",
    )
    builder.add_separator()
    builder.add_item(
        "Reload Configuration Values from File",
        handle_reload_configuration,
        description="Reload configuration values from the Excel file after making changes",
    )
    builder.add_separator()
    builder.add_item(
        "Exit back to Main Menu",
        lambda: None,
        exit_menu=True,
        description="Return to the main menu",
    )
    return builder.build()


def get_simulation_menu():
    """Create and return the simulation menu."""
    builder = MenuBuilder("Simulation Menu")
    builder.add_item(
        "Explore Simulated Data",
        handle_view_simulated_data_examples,
        description="Interactive navigation through installation, facility, system, and work-order entities",
    )
    builder.add_item(
        "View Single Facility + System",
        handle_view_facility_and_system,
        description="Generate one installation and inspect a selected facility/system pair",
    )
    builder.add_item(
        "Quick Generate & Stats",
        handle_quick_generate,
        description="Quickly generate data and view summary statistics",
    )
    builder.add_item(
        "Generate & Export Dataset",
        handle_generate_data,
        description="Full wizard to generate and export data (CSV, Excel)",
    )
    builder.add_separator()
    builder.add_item(
        "Back to Main Menu",
        lambda: None,
        exit_menu=True,
        description="Return to the main menu",
    )
    return builder.build()


def get_main_menu():
    """Create and return the main menu."""

    def handle_configuration() -> None:
        """Navigate to configuration menu."""
        get_configuration_menu().run()

    def handle_simulation() -> None:
        """Navigate to simulation menu."""
        get_simulation_menu().run()

    # def handle_ml_prediction() -> None:
    #     """Navigate to ML prediction menu."""
    #     get_ml_prediction_menu().run()

    def handle_exit() -> None:
        """Exit the application."""
        console.print("\n[cyan]Exiting MIDAS[/cyan]\n")

    builder = MenuBuilder("Main Menu")
    builder.add_item(
        "Configuration",
        handle_configuration,
        description="View and manage facility types, system types, and configuration values",
    )
    builder.add_item(
        "Simulation",
        handle_simulation,
        description="Generate and explore simulated installations, facilities, and systems",
    )
    # builder.add_item(
    #     "ML Prediction",
    #     handle_ml_prediction,
    #     description="Train models, extract features, and predict degradation timing",
    # )
    builder.add_separator()
    builder.add_item(
        "Exit",
        handle_exit,
        exit_menu=True,
        description="Exit the MIDAS application",
    )
    return builder.build()
