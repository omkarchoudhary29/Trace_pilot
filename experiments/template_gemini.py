import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.prompting.system_prompts import TRACEPILOT_SYSTEM_PROMPT
from app.prompting.templates import build_debugging_prompt

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL")

if not api_key or not model:
    raise ValueError("Gemini configuration is missing.")

client = genai.Client(api_key=api_key)

error_text = """
Traceback (most recent call last):
  File "calculator.py", line 15, in divide
    return a / b
ZeroDivisionError: division by zero
"""

prompt = build_debugging_prompt(
    error_text=error_text,
    additional_context="The application crashes when a user divides two numbers.",
    programming_language="Python"
)

response = client.models.generate_content(
    model=model,
    contents=prompt,
    config=types.GenerateContentConfig(
        system_instruction=TRACEPILOT_SYSTEM_PROMPT
    )
)

print("\nTRACEPILOT TEMPLATE ANALYSIS")
print("=" * 55)
print(response.text)