# C:\Users\PC\SwarmMultiAgent\agency.py

import sys
import os
from pathlib import Path

# ==============================================================================
# **PERMANENT, STABLE FIX (Required for tool visibility):**
# Explicitly add the project root to the system path.
# ==============================================================================
project_root = str(Path(__file__).parent.resolve())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Core Library Imports ---
from agency_swarm import Agency, Agent
from schemas.reports import QualityAssuranceReport

# --- Config Imports ---
import config

# --- Agent Imports (Clean, Absolute Paths) ---
from agency.ceo_agent.ceo_agent import CEOAgent
from agency.god_agent.god_agent import GodAgent
from agency.architecture_agent.architecture_agent import ArchitectureAgent
from agency.developer_agent.developer_agent import DeveloperAgent
from agency.database_agent.database_agent import DatabaseAgent
from agency.security_officer_agent.security_officer_agent import SecurityOfficerAgent
from agency.testing_qa_agent.testing_qa_agent import TestingQAAgent
from agency.DocumentVaultAgent.DocumentVaultAgent import DocumentVaultAgent 
from agency.documentation_agent.documentation_agent import DocumentationAgent
from mvp_v1.training.advisory_agent import AdvisoryAgent
from agency.operations_agent.operations_agent import OperationsAgent
from agency.financier_agent.financier_agent import FinancierAgent
from agency.training_agent.training_agent import LanguageCoachAgent
from agency.student_progress_agent.student_progress_agent import StudentProgressAgent
from mvp_v1.legal.visa_compliance_agent_swarm import VisaComplianceAgent
from agency.messenger_agent.messenger_agent import MessengerAgent
from agency.vr_environment_agent.vr_environment_agent import VREnvironmentAgent
from agency.support_agent.support_agent import SupportAgent


# --- 1. Agent Instantiation ---
ceo = CEOAgent()
god_agent = GodAgent()
architecture_agent = ArchitectureAgent()
developer_agent = DeveloperAgent()
database_agent = DatabaseAgent()
security_officer_agent = SecurityOfficerAgent()
testing_qa_agent = TestingQAAgent()
document_vault_agent = DocumentVaultAgent()
documentation_agent = DocumentationAgent()
advisory_agent = AdvisoryAgent()
operations_agent = OperationsAgent()
financier_agent = FinancierAgent()
training_agent = LanguageCoachAgent()
student_progress_agent = StudentProgressAgent()
visa_compliance_agent = VisaComplianceAgent()
messenger_agent = MessengerAgent()
vr_environment_agent = VREnvironmentAgent()
support_agent = SupportAgent()


# --- 2. Agency Communication Structure ---
# Define communication flows: (sender, receiver) tuples
communication_flows = [
    # Level 1: User Facing
    (ceo, god_agent),

    # Level 2: Core Manager to Specialized Agents
    (god_agent, architecture_agent),
    (god_agent, developer_agent),
    (god_agent, database_agent),
    (god_agent, security_officer_agent),
    (god_agent, testing_qa_agent),
    (god_agent, document_vault_agent),
    (god_agent, documentation_agent),
    (god_agent, advisory_agent),  # For candidate concerns and troubleshooting
    (god_agent, operations_agent),  # For wisdom reports and platform health
    (god_agent, financier_agent),  # For fee collection and financial records
    (god_agent, training_agent),  # For skill interviews and curriculum tracking
    (god_agent, student_progress_agent),  # For Memory Layer and analytics
    (training_agent, student_progress_agent),  # LanguageCoachAgent records performance
    (god_agent, visa_compliance_agent),  # For visa compliance and auto-compliance checking
    (god_agent, messenger_agent),  # For candidate notifications and communications
    (visa_compliance_agent, messenger_agent),  # Auto-notify when compliance passes
    (god_agent, vr_environment_agent),  # For VR/AR scene management (Phase 2)
    (training_agent, vr_environment_agent),  # TrainingAgent coordinates VR scenes
    (god_agent, support_agent),  # For legal/personal advice about life in Japan
]

# --- 3. Shared user context from config.py ---
user_context = {
    "phase_2_enabled": config.PHASE_2_ENABLED,
    "corridors": config.CORRIDORS,
    "visa_modes": config.VISA_MODES,
    "trilingual_support": config.TRILINGUAL_SUPPORT,
}

# Create Agency with modern API format
agency = Agency(
    ceo,  # Entry point agent (user-facing)
    communication_flows=communication_flows,
    name="XploreKodo SACM Agency (9-Agent System)",
    user_context=user_context,
)

if __name__ == '__main__':
    print(f"--- {agency.name} is starting ---")
    agency.terminal_demo()