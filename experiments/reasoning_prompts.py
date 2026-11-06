import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.prompting.reasoning_prompts import REASONING_DEBUGGING_PROMPT
from app.prompting.system_prompts import TRACEPILOT_SYSTEM_PROMPT

# 1. Load configuration
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL")

if not api_key or not model:
    raise ValueError("Gemini configuration is missing.")

# 2. Create Gemini client
client = genai.Client(api_key=api_key)

# 3. Provide an error
error_text = """
Traceback (most recent call last):
  File "payment.py", line 20, in process_payment
    total = price * quantity
TypeError: can't multiply sequence by non-int of type 'float'
"""

# 4. Fill the reasoning-oriented prompt
prompt = REASONING_DEBUGGING_PROMPT.format(
    error_text=error_text
)

# 5. Send request to Gemini
response = client.models.generate_content(
    model=model,
    contents=prompt,
    config=types.GenerateContentConfig(
        system_instruction=TRACEPILOT_SYSTEM_PROMPT
    )
)

# 6. Display the report
print("\nTRACEPILOT REASONING-ORIENTED ANALYSIS")
print("=" * 60)
print(response.text)