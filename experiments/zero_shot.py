
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.prompting.system_prompts import TRACEPILOT_SYSTEM_PROMPT

# 1. Load environment configuration
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL")

if not api_key or not model:
    raise ValueError("Gemini configuration is missing.")


# 2. Create Gemini client
client = genai.Client(api_key=api_key)


# 3. Define the error to analyze
error_text = """
Traceback (most recent call last):
  File "reader.py", line 8, in <module>
    open("data.csv")
FileNotFoundError: [Errno 2] No such file or directory: 'data.csv'
"""


# 4. Create a zero-shot prompt
zero_shot_prompt = f"""
Analyze the following Python error.

ERROR:
{error_text}

Provide:
1. Error classification.
2. Simple explanation.
3. Likely root cause.
4. Evidence from the traceback.
5. Recommended debugging steps.
6. Verification steps.

Do not use any external assumptions.
Clearly distinguish facts from hypotheses.
"""


# 5. Send the prompt to Gemini
response = client.models.generate_content(
    model=model,
    contents=zero_shot_prompt,
    config=types.GenerateContentConfig(
        system_instruction=TRACEPILOT_SYSTEM_PROMPT
    )
)


# 6. Display the response
print("\nZERO-SHOT DEBUGGING EXPERIMENT")
print("=" * 55)

print(response.text)
