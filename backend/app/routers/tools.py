"""Biomni tool and dataset browser API.

To register this router, add to main.py:

    from .routers import tools
    app.include_router(tools.router, prefix="/api/v1", tags=["tools"])
"""

import ast
import logging
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Query

from ..schemas.tools import (
    Dataset,
    DatasetListResponse,
    ToolListResponse,
    ToolModule,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Resolve paths relative to this file -> project root -> Biomni
_PROJECT_ROOT = Path(__file__).resolve().parents[3]  # backend/app/routers -> project root
_TOOL_DIR = _PROJECT_ROOT / "Biomni" / "biomni" / "tool"
_TOOL_DESC_DIR = _TOOL_DIR / "tool_description"
_ENV_DESC_PATH = _PROJECT_ROOT / "Biomni" / "biomni" / "env_desc.py"

# Domains to skip (not actual tool domains)
_SKIP_FILES = {
    "__init__.py",
    "tool_registry.py",
    "database.py",
    "support_tools.py",
}


def _count_functions(filepath: Path) -> int:
    """Count top-level function definitions in a Python file using AST."""
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
        return sum(1 for node in ast.iter_child_nodes(tree) if isinstance(node, ast.FunctionDef))
    except Exception:
        return 0


def _get_first_docstring(filepath: Path) -> str:
    """Extract the module-level docstring from a Python file."""
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
        docstring = ast.get_docstring(tree)
        return docstring.split("\n")[0] if docstring else ""
    except Exception:
        return ""


def _load_tool_descriptions(domain: str) -> dict[str, str]:
    """Load structured tool descriptions from tool_description directory."""
    desc_file = _TOOL_DESC_DIR / f"{domain}.py"
    if not desc_file.exists():
        return {}
    try:
        # Use AST to safely extract the description list
        tree = ast.parse(desc_file.read_text(encoding="utf-8"))
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "description":
                        # Evaluate the list literal safely
                        value = ast.literal_eval(node.value)
                        return {
                            item["name"]: item.get("description", "")
                            for item in value
                            if isinstance(item, dict) and "name" in item
                        }
    except Exception as e:
        logger.debug("Could not parse tool descriptions for %s: %s", domain, e)
    return {}


@lru_cache(maxsize=1)
def _scan_tools() -> list[ToolModule]:
    """Walk the Biomni tool directory and build a catalog of tool modules."""
    tools: list[ToolModule] = []

    if not _TOOL_DIR.is_dir():
        logger.warning("Biomni tool directory not found: %s", _TOOL_DIR)
        return tools

    for py_file in sorted(_TOOL_DIR.iterdir()):
        if not py_file.is_file() or not py_file.suffix == ".py":
            continue
        if py_file.name in _SKIP_FILES:
            continue

        domain = py_file.stem
        func_count = _count_functions(py_file)
        module_docstring = _get_first_docstring(py_file)

        # Load structured descriptions from tool_description dir
        desc_map = _load_tool_descriptions(domain)

        # Build a summary description for the domain
        if module_docstring:
            domain_desc = module_docstring
        elif desc_map:
            # Use first few function descriptions as summary
            first_descs = list(desc_map.values())[:3]
            domain_desc = "; ".join(
                d[:80] + "..." if len(d) > 80 else d for d in first_descs if d
            )
            if len(desc_map) > 3:
                domain_desc += f" (+{len(desc_map) - 3} more)"
        else:
            domain_desc = f"{domain.replace('_', ' ').title()} tools"

        tools.append(
            ToolModule(
                domain=domain,
                name=domain,
                description=domain_desc,
                function_count=func_count,
            )
        )

    return tools


@lru_cache(maxsize=1)
def _scan_datasets() -> list[Dataset]:
    """Parse env_desc.py to extract data lake and library datasets."""
    datasets: list[Dataset] = []

    if not _ENV_DESC_PATH.is_file():
        logger.warning("env_desc.py not found: %s", _ENV_DESC_PATH)
        return datasets

    try:
        tree = ast.parse(_ENV_DESC_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error("Failed to parse env_desc.py: %s", e)
        return datasets

    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue

            if target.id == "data_lake_dict":
                category = "data_lake"
            elif target.id == "library_content_dict":
                category = "library"
            else:
                continue

            try:
                data = ast.literal_eval(node.value)
                for name, desc in data.items():
                    datasets.append(
                        Dataset(name=name, description=desc, category=category)
                    )
            except Exception as e:
                logger.error("Failed to evaluate %s: %s", target.id, e)

    return datasets


# --- Endpoints ---


@router.get("/tools", response_model=ToolListResponse)
async def list_tools(search: str | None = Query(default=None, description="Search keyword")):
    """List all Biomni tool domains."""
    tools = _scan_tools()
    if search:
        q = search.lower()
        tools = [
            t for t in tools
            if q in t.domain.lower() or q in t.name.lower() or q in t.description.lower()
        ]
    return ToolListResponse(tools=tools, total=len(tools))


@router.get("/tools/{domain}", response_model=ToolListResponse)
async def get_tools_by_domain(domain: str):
    """Get tool functions in a specific domain."""
    all_tools = _scan_tools()
    # Check if domain exists
    domain_tool = next((t for t in all_tools if t.domain == domain), None)
    if domain_tool is None:
        return ToolListResponse(tools=[], total=0)

    # Load detailed function-level info from tool_description
    desc_map = _load_tool_descriptions(domain)
    py_file = _TOOL_DIR / f"{domain}.py"

    if desc_map:
        # Return individual functions from the description
        functions = [
            ToolModule(
                domain=domain,
                name=name,
                description=desc[:200] if desc else "",
                function_count=1,
            )
            for name, desc in desc_map.items()
        ]
    elif py_file.exists():
        # Fall back to AST parsing for function names and docstrings
        functions = []
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.FunctionDef):
                    docstring = ast.get_docstring(node) or ""
                    first_line = docstring.split("\n")[0] if docstring else ""
                    functions.append(
                        ToolModule(
                            domain=domain,
                            name=node.name,
                            description=first_line[:200],
                            function_count=1,
                        )
                    )
        except Exception:
            pass
    else:
        functions = []

    return ToolListResponse(tools=functions, total=len(functions))


@router.get("/datasets", response_model=DatasetListResponse)
async def list_datasets(search: str | None = Query(default=None, description="Search keyword")):
    """List data lake datasets and libraries."""
    datasets = _scan_datasets()
    if search:
        q = search.lower()
        datasets = [
            d for d in datasets
            if q in d.name.lower() or q in d.description.lower() or q in d.category.lower()
        ]
    return DatasetListResponse(datasets=datasets, total=len(datasets))
