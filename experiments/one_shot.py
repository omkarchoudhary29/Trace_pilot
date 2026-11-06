import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.prompting.system_prompts import TRACEPILOT_SYSTEM_PROMPT

# 1. Load environment variables
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL")

if not api_key or not model:
    raise ValueError("Gemini configuration is missing.")

# 2. Create Gemini client
client = genai.Client(api_key=api_key)

# 3. One example: input and expected output
example_error = """
TypeError: can only concatenate str (not "int") to str
"""

example_output = """
Error classification: TypeError

Explanation:
Python cannot directly concatenate a string and an integer.

Likely root cause:
The program is attempting to combine values of incompatible types.

Evidence:
The error explicitly identifies a string and an integer.

Recommended debugging steps:
1. Inspect the variables being concatenated.
2. Check their data types using type().
3. Convert the integer to a string if text concatenation is intended.

Verification:
Run the operation again and confirm that the values are handled
using compatible types.
"""

# 4. New error for the model to analyze
new_error = """
Traceback (most recent call last):
  File "reader.py", line 8, in <module>
    open("data.csv")
FileNotFoundError: [Errno 2] No such file or directory: 'data.csv'
"""

# 5. Build one-shot prompt
one_shot_prompt = f"""
You are given one example of a debugging task.

EXAMPLE INPUT:
{example_error}

EXAMPLE OUTPUT:
{example_output}

Now analyze the following NEW error.
Do not copy the example's diagnosis.
Follow its structure and level of detail.

NEW INPUT:
{new_error}

Produce:
1. Error classification.
2. Explanation.
3. Likely root cause.
4. Evidence.
5. Recommended debugging steps.
6. Verification steps.

Do not invent missing information.
Distinguish facts from hypotheses.
"""

# 6. Call Gemini
response = client.models.generate_content(
    model=model,
    contents=one_shot_prompt,
    config=types.GenerateContentConfig(
        system_instruction=TRACEPILOT_SYSTEM_PROMPT
    )
)

# 7. Display output
print("\nONE-SHOT DEBUGGING EXPERIMENT")
print("=" * 55)
print(response.text)