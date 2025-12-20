# C:\Users\PC\SwarmMultiAgent\agency\code_writer_tool.py

import os
from pathlib import Path
from agency_swarm.tools import BaseTool
from pydantic import Field, BeforeValidator
from typing import Annotated

# Define the base directory (project root) for security and scoping
# This prevents the agent from writing outside your main project folder
BASE_DIR = Path(os.getcwd())

# Define a restricted path type for Pydantic validation
# This ensures file paths are relative and stay within the project structure
PathValidator = BeforeValidator(lambda v: Path(v) if v else None)
RestrictedPath = Annotated[Path, PathValidator]


class CodeWriterTool(BaseTool):
    """
    A tool used by agents (Developer, Testing/QA) to safely read, write, and manage 
    code files within the project structure. All paths must be relative to the 
    project root and must not escape the project directory.
    """
    name: str = Field(
        default="CodeWriterTool", 
        description="Tool for file system operations (read, write, delete) confined to the project directory."
    )

    def run(self, action: str, file_path: RestrictedPath, content: str = None):
        """
        Executes a file system operation.

        :param action: 'write', 'read', or 'delete'.
        :param file_path: The relative path to the file (e.g., 'src/api/user.py').
        :param content: Required only for the 'write' action.
        :return: Success message or error details.
        """
        full_path = BASE_DIR / file_path
        
        # Security Check: Prevent directory traversal outside of BASE_DIR
        if not full_path.resolve().is_relative_to(BASE_DIR.resolve()):
            return f"Error: Attempted file operation outside the project root: {file_path}"
        
        try:
            if action == 'write':
                if content is None:
                    return "Error: 'content' is required for the 'write' action."
                
                # Ensure the parent directory exists
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return f"Success: File written to {file_path}"
            
            elif action == 'read':
                if not full_path.exists():
                    return f"Error: File not found at {file_path}"
                
                with open(full_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            elif action == 'delete':
                if not full_path.exists():
                    return f"Error: File not found at {file_path}"
                
                os.remove(full_path)
                return f"Success: File deleted at {file_path}"
                
            else:
                return f"Error: Invalid action '{action}'. Must be 'write', 'read', or 'delete'."
                
        except Exception as e:
            return f"File operation failed for {file_path}: {str(e)}"

# Example Usage (for testing purposes, not run by the agent)
# if __name__ == "__main__":
#     tool = CodeWriterTool()
#     # Write a file
#     print(tool.run('write', 'test_output.txt', 'This is a test file.'))
#     # Read the file
#     print(tool.run('read', 'test_output.txt'))
#     # Delete the file
#     print(tool.run('delete', 'test_output.txt'))

