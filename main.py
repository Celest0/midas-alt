"""Main entry point for MIDAS application."""
import os
os.system("chcp 65001 > nul")

import logging
from pathlib import Path
from rich.console import Console

from src.cli.cli import run_cli
from src.config import configure_logging


def main():
    """Initialize logging and start the CLI."""
    configure_logging()
    run_cli()


if __name__ == "__main__":
    main()
