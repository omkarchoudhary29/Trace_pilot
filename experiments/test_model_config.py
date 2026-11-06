
from app.llm.model_config import create_generation_config

config = create_generation_config(
    system_instruction="You are a software debugging assistant."
)

print("MODEL CONFIGURATION TEST")
print("=" * 45)

print("Temperature:", config.temperature)
print("Top P:", config.top_p)
print("Max output tokens:", config.max_output_tokens)
print("System instruction:", config.system_instruction)
