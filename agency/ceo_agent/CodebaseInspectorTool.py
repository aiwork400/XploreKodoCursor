from agency_swarm.tools import BaseTool
from pydantic import Field
import requests

# Define the local server endpoint
INSPECTOR_ENDPOINT = "http://127.0.0.1:5001/inspect"

class CodebaseInspectorTool(BaseTool):
    """
    A powerful tool that connects to a local server to read the actual content 
    of project files by path (e.g., 'agency.py' or 'agency/DocumentVaultAgent/DocumentVaultAgent.py'). 
    Use this to debug class inheritance and verify imports across inter-linked files.
    """
    name: str = Field(
        default="CodebaseInspectorTool",
        description="Tool for inspecting codebase files via local server."
    )

    def run(self, file_path: str):
        """
        Inspect a file in the codebase by reading its content from the local inspector server.
        
        :param file_path: The relative path to the file to inspect (e.g., 'agency.py', 'venv/Lib/site-packages/agency_swarm/agency/core.py').
        :return: The file content or an error message.
        """
        try:
            # Send the request to the local Flask server using POST, as expected by the server
            response = requests.post(
                INSPECTOR_ENDPOINT, 
                json={'path': file_path} # Use json for the POST body
            )
            response.raise_for_status()  # Raise exception for bad status codes
            
            data = response.json()

            if "error" in data:
                return f"Tool Error: {data['error']}"

            # Return the file content
            return f"--- File Content: {data['path']} ---\n{data['content']}"

        except requests.exceptions.RequestException as e:
            return f"Error connecting to local Inspector Server. Ensure 'local_inspector_server.py' is running on 127.0.0.1:5001. Error: {e}"