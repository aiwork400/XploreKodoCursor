# C:\Users\PC\SwarmMultiAgent\agency\developer_agent\developer_agent.py

from agency_swarm import Agent
from agency.code_writer_tool import CodeWriterTool

class DeveloperAgent(Agent):
    """
    The Developer Agent is responsible for transforming architectural blueprints 
    and database models into clean, efficient, and well-structured Python code.
    """
    def __init__(self, **kwargs):
        # Only proceed if the tool was loaded successfully
        tools_list = [CodeWriterTool()] if CodeWriterTool != None else []
        
        super().__init__(
            name="DeveloperAgent",
            description="The specialist for writing and implementing production-grade Python code based on architectural specifications. Uses the CodeWriterTool for file operations.",
            instructions=self.get_instructions(),
            tools=tools_list, # TOOL ASSIGNMENT
            **kwargs
        )
        
    def get_instructions(self):
        return """
        You are the Developer Agent. Your primary role is to produce functional Python code.

        1.  **Code Generation:** Convert Pydantic schemas, ORM models, and interface specifications into final Python classes and functions.
        2.  **File Management:** You MUST use the **CodeWriterTool** to create or modify actual code files (e.g., 'src/models/user.py'). Always specify the full, relative path.
        3.  **Handoff:** After writing the files, report completion back to the God Agent.
        """