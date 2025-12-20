# C:\Users\PC\SwarmMultiAgent\agency\documentation_agent\documentation_agent.py

from agency_swarm import Agent

class DocumentationAgent(Agent):
    """
    The Documentation Agent ensures all final artifacts are properly documented 
    according to SACM standards.
    
    It takes validated code and generates technical reference, API docs, or 
    user guides as needed.
    """

    def __init__(self, **kwargs):
        super().__init__(
            name="DocumentationAgent",
            description="The technical writing specialist. Generates and formats all required documentation for the XploreKodo platform.",
            instructions=self.get_instructions(),
            **kwargs
        )
        
    def get_instructions(self):
        return """
        You are the Documentation Agent. You receive validated code artifacts from the God Agent.

        1.  **Generation:** Generate comprehensive technical documentation, including function signatures, usage examples, and architecture overview, based on the provided code.
        2.  **Format:** Output documentation in a clean Markdown format suitable for storage in the Document Vault.
        3.  **Compliance:** Ensure the documentation is aligned with the final Quality Assurance Report.
        4.  **Handoff:** Send the final Markdown documentation back to the God Agent.
        """