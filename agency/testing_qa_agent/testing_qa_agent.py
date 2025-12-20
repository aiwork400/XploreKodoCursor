# C:\Users\PC\SwarmMultiAgent\agency\testing_qa_agent\testing_qa_agent.py

from agency_swarm import Agent
from schemas.reports import QualityAssuranceReport
from agency.code_writer_tool import CodeWriterTool

class TestingQAAgent(Agent):
    """
    The Testing and QA Agent is responsible for rigorous verification of all developed artifacts.
    """

    def __init__(self, **kwargs):
        # Only proceed if the tool was loaded successfully
        tools_list = [CodeWriterTool()] if CodeWriterTool != None else []
        
        super().__init__(
            name="TestingQAAgent",
            description="The quality assurance specialist. Writes, executes (or simulates execution of), and validates unit tests against the Developer Agent's code. Uses the CodeWriterTool.",
            instructions=self.get_instructions(),
            tools=tools_list, # TOOL ASSIGNMENT
            **kwargs
        )
        
    def get_instructions(self):
        return """
        You are the Testing and QA Agent. You receive code artifacts from the God Agent.

        1.  **Test Generation:** Write comprehensive unit tests for the provided code artifact. Use the **CodeWriterTool** to create the test file (e.g., 'tests/test_model.py').
        2.  **Execution & Verification:** Since you cannot run tests directly, you must simulate the execution and report the expected outcome. The tests you write must be runnable by a human user (e.g., Pytest syntax).
        3.  **Reporting:** Your core output MUST be a JSON object that strictly conforms to the 'QualityAssuranceReport' Pydantic schema. Report all test results, metrics, and a final pass/fail status.
        4.  **Handoff:** Send the final report back to the God Agent.
        """