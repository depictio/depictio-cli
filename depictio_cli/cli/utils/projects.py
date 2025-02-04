from typing import Optional
from typeguard import typechecked
from depictio_cli.cli.utils.rich_utils import rich_print_checked_statement, rich_print_section_separator
from depictio_cli.cli.utils.workflows import process_workflow_helper
from depictio_cli.logging import logger
from depictio_models.models.cli import CLIConfig
from depictio_models.models.projects import Project


@typechecked
def process_project_helper(
    CLI_config: CLIConfig,
    project_config: Project,
    workflow_name: Optional[str] = None,
    data_collection_tag: Optional[str] = None,
    reprocess_runs: bool = False,
    update_files: bool = False,
):
    """
    Process workflows within a project, optionally filtering by workflow name.

    Args:
        cli_config (dict): CLI configuration settings.
        project_config (dict): Project configuration containing workflows.
        workflow_name (str, optional): Specific workflow name to process.
                                       If None, all workflows are processed.
        data_collection_tag (str, optional): Specific data collection tag to process.
                                             If None, all data collections are processed.
    """
    logger.info(f"Processing project: {project_config.name}")
    rich_print_section_separator("Scanning files")
    rich_print_checked_statement(f"Processing project: {project_config.name}", "info")

    # Determine which workflows to process
    workflows = project_config.workflows

    if workflow_name:
        # Filter workflows if specific name requested
        rich_print_checked_statement(f"Filtering workflows for name: {workflow_name}", "info")
        workflows = [wf for wf in workflows if wf.name == workflow_name]

        if not workflows:
            logger.error(f"No workflow found with name: {workflow_name}")
            rich_print_checked_statement(f"No workflow found with name: {workflow_name}", "error")

    # Process selected workflows
    for workflow in workflows:
        logger.info(f"Processing workflow: {workflow.workflow_tag}")
        rich_print_checked_statement(f"Processing workflow: {workflow.workflow_tag}", "info")
        process_workflow_helper(CLI_config=CLI_config, workflow=workflow, data_collection_tag=data_collection_tag, reprocess_runs=reprocess_runs, update_files=update_files)
        rich_print_checked_statement(f"Workflow {workflow.workflow_tag} processed successfully", "success")
