from app.prompting.templates import build_debugging_prompt

error_text = """
ZeroDivisionError: division by zero
"""

prompt = build_debugging_prompt(
    error_text=error_text,
    additional_context="The error occurred inside a calculator application.",
    programming_language="Python"
)

print("\nGENERATED PROMPT")
print("=" * 50)
print(prompt)