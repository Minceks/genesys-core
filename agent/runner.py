from typing import Any

from .daytona_workspace import get_workspace


# ============================================================
# BUILD
# ============================================================

def run_build(
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    """
    Run npm run build inside the project's Daytona sandbox.
    """

    workspace = get_workspace(
        project_id
    )

    return workspace.run_build()


# ============================================================
# START PREVIEW
# ============================================================

def start_preview(
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    """
    Start or reuse the Vite preview inside the project's
    Daytona sandbox.
    """

    workspace = get_workspace(
        project_id
    )

    return workspace.start_preview()


# ============================================================
# STOP PREVIEW
# ============================================================

def stop_preview(
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    """
    Stop the Vite preview inside the project's Daytona sandbox.
    """

    workspace = get_workspace(
        project_id
    )

    return workspace.stop_preview()

# ============================================================
# M6.5 — PROJECT DIFF
# ============================================================

def get_project_diff(
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    """
    Return the current Git diff for the project workspace.
    """
    workspace = get_workspace(project_id)
    return workspace.get_diff()

# ============================================================
# RESET PROJECT
# ============================================================

def reset_project(
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    """
    Reset the project working tree to origin/main.
    """

    workspace = get_workspace(
        project_id
    )

    return workspace.reset_project()

# ============================================================
# WORKSPACE STATE
# ============================================================

def workspace_state(
    project_id: str = "genesys-project",
) -> dict[str, Any]:
    """
    Return the current Daytona workspace state.
    """

    workspace = get_workspace(
        project_id
    )

    return workspace.state()