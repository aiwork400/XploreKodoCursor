"""
Agency module - exports the main Agency instance for agent-to-agent communication.

The agency instance is created in the root agency.py file and exported here
to avoid namespace conflicts between the agency module and the agency variable.
"""

# Fix Import Path: Import agency instance from root agency.py file
# Resolve Namespace Conflict: Use importlib to avoid circular imports
import sys
from pathlib import Path
import importlib.util

# Get project root (parent of agency/ folder)
project_root = Path(__file__).parent.parent.resolve()

# Add project root to path if not already there
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import the agency instance from the root agency.py file
# Use importlib to load it as a separate module to avoid circular imports
# Cleanup __init__.py: Ensure no circular import by explicitly loading root agency.py, not self
agency_py_path = project_root / "agency.py"
if agency_py_path.exists():
    try:
        # Load the root agency.py as a module (using unique module name to avoid conflicts)
        # This prevents any potential circular import if agency.py tries to import from agency module
        spec = importlib.util.spec_from_file_location("agency_swarm_setup_module", agency_py_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not create spec for {agency_py_path}")
        
        agency_swarm_setup = importlib.util.module_from_spec(spec)
        # Execute the module to create the agency instance
        # Check line 33: Ensure error handling doesn't suppress original error details
        try:
            spec.loader.exec_module(agency_swarm_setup)
        except SyntaxError as syntax_err:
            # Preserve full syntax error details including line numbers
            raise ImportError(
                f"Syntax error in {agency_py_path} at line {syntax_err.lineno}: {syntax_err.msg}\n"
                f"File: {syntax_err.filename}, Line: {syntax_err.lineno}, Text: {syntax_err.text}"
            ) from syntax_err
        except IndentationError as indent_err:
            # Preserve full indentation error details
            raise ImportError(
                f"Indentation error in {agency_py_path} at line {indent_err.lineno}: {indent_err.msg}\n"
                f"File: {indent_err.filename}, Line: {indent_err.lineno}, Text: {indent_err.text}"
            ) from indent_err
        except Exception as exec_err:
            # Preserve other import/execution errors with full traceback context
            raise ImportError(
                f"Error executing {agency_py_path}: {type(exec_err).__name__}: {exec_err}\n"
                f"This may indicate indentation issues, missing imports, or other syntax problems."
            ) from exec_err
        
        # Get the agency instance from the module
        agency = getattr(agency_swarm_setup, "agency", None)
        if agency is None:
            raise ImportError("agency instance not found in agency.py - make sure it's created as 'agency = Agency(...)'")
    except ImportError:
        # Re-raise ImportError as-is (it already has helpful details)
        raise
    except Exception as e:
        # If import fails, set to None and raise a helpful error
        agency = None
        raise ImportError(f"Failed to import agency instance from {agency_py_path}: {type(e).__name__}: {e}") from e
else:
    agency = None
    raise ImportError(f"Could not find agency.py at {agency_py_path}")

# Export the agency instance
__all__ = ["agency"]
