
from app.llm.api_handler import generate_response

prompt = """
Explain this Python error in simple terms:

ModuleNotFoundError: No module named 'pandas'
"""

system_instruction = """
You are a helpful Python debugging assistant.
Explain errors accurately and do not invent missing information.
"""

response = generate_response(
    prompt=prompt,
    system_instruction=system_instruction
)

print("\nGEMINI API HANDLER TEST")
print("=" * 50)
print(response)
