# validate_schemas.py
from pydantic import ValidationError
from schemas.artifacts import ArchitectureBlueprint, PydanticModelDefinition, ComponentInterface, MethodSignature
import json

print("--- Testing ArchitectureBlueprint Schema Validation ---")

# 1. Define a sample Pydantic Model specification
sample_model_spec = PydanticModelDefinition(
    model_name="AgentConfigSchema",
    fields={
        "agent_name": "str",
        "model_id": "str",
        "instructions_path": "Path"
    },
    description="Configuration structure for any SACM Agent."
)

# 2. Define a sample Component Interface (The DocumentVault class)
sample_interface_spec = ComponentInterface(
    component_type="AgentTool",
    class_name="DocumentVaultTool",
    methods=[
        MethodSignature(
            name="commit_artifact",
            arguments={"task_id": "str", "artifact_files": "list"},
            return_type="bool",
            docstring="Atomically commits verified artifacts to the vault."
        )
    ],
    description="The primary tool for the DocumentVault Agent."
)

# 3. Combine them into the final Architecture Blueprint
sample_blueprint_data = {
    "task_id": "SACM-001-A",
    "component_name": "Initial_Agent_Schemas",
    "models": [sample_model_spec.model_dump()],
    "interfaces": [sample_interface_spec.model_dump()]
}

try:
    blueprint = ArchitectureBlueprint(**sample_blueprint_data)
    print("\n✅ Validation Successful! The ArchitectureBlueprint structure is valid.")
    print(f"Task ID: {blueprint.task_id}")
    print(f"Models to build: {len(blueprint.models)}")
    
    # Optional: Print the JSON output the Architecture Agent would produce
    # print("\n--- Sample JSON Output ---")
    # print(json.dumps(blueprint.model_dump(), indent=4))

except ValidationError as e:
    print("\n❌ Validation Failed! Schema definition needs correction.")
    print(e)
    
print("-" * 40)