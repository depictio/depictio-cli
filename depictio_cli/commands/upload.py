import typer
from typing import Optional

app = typer.Typer()

@app.command()
def setup(
    config_path: str = typer.Option(
        ...,
        "--config_path",
        help="Path to the YAML configuration file",
    ),
    # workflow_tag: Optional[str] = typer.Option(None, "--workflow_tag", help="Workflow name to be created"),
    update: Optional[bool] = typer.Option(False, "--update", help="Update the workflow if it already exists"),
    erase_all: Optional[bool] = typer.Option(False, "--erase_all", help="Erase all workflows and data collections"),
    scan_files: Optional[bool] = typer.Option(False, "--scan_files", help="Scan files for all data collections of the workflow"),
    data_collection_tag: Optional[str] = typer.Option(None, "--data_collection_tag", help="Data collection tag to be scanned"),
    token: Optional[str] = typer.Option(
        None,  # Default to None (not specified)
        "--token",
        help="Optionally specify a token to be used for authentication",
    ),
):
    """
    Create a new workflow from a given YAML configuration file.
    """