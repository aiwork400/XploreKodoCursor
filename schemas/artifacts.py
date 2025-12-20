from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal, Optional

# --- Sub-Schemas for Component Definition ---

class MethodSignature(BaseModel):
    """
    Defines a single method or function signature within a component.
    """
    name: str = Field(..., description="The name of the method (e.g., 'authenticate_user').")
    arguments: Dict[str, str] = Field(..., description="A dictionary of argument names and their type hints (e.g., {'user_id': 'str', 'password': 'str'}).")
    return_type: str = Field(..., description="The return type hint (e.g., 'bool' or 'UserSchema').")
    docstring: str = Field(..., description="A clear, single-paragraph description of the method's purpose.")

class ComponentInterface(BaseModel):
    """
    Defines the structure for a functional class or service component.
    This is the blueprint for the Developer Agent to write a Python class.
    """
    component_type: Literal["Service", "Utility", "AgentTool"] = Field("Service", description="The high-level category of the component.")
    class_name: str = Field(..., description="The exact name of the Python class to be implemented (e.g., 'AuthService').")
    base_classes: List[str] = Field(default=["BaseService"], description="A list of classes this component must inherit from.")
    methods: List[MethodSignature] = Field(..., description="A list of all required methods for this class.")
    description: str = Field(..., description="A detailed explanation of the class's responsibility.")

class PydanticModelDefinition(BaseModel):
    """
    Defines a single Pydantic data model structure.
    This is the blueprint for the Developer Agent to write a pydantic.BaseModel.
    """
    model_name: str = Field(..., description="The exact name of the Pydantic model (e.g., 'UserSchema').")
    fields: Dict[str, str] = Field(..., description="A dictionary of field names and their type hints (e.g., {'id': 'str', 'email': 'EmailStr'}).")
    description: str = Field(..., description="A detailed description of the model's purpose and contents.")
    
# --- Top-Level Blueprint Schema ---

class ArchitectureBlueprint(BaseModel):
    """
    The main structured output from the Architecture Agent to the God Agent.
    This document contains ALL specifications for a single development task.
    """
    task_id: str = Field(..., description="A unique identifier for the development task (e.g., 'AUTH-V1-01').")
    component_name: str = Field(..., description="The name of the module or feature being built (e.g., 'UserAuthentication').")
    models: List[PydanticModelDefinition] = Field(default=[], description="A list of Pydantic models to be created.")
    interfaces: List[ComponentInterface] = Field(default=[], description="A list of service or utility interfaces to be implemented.")