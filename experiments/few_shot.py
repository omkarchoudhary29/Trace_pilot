
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


# 3. Define multiple examples
examples = [
    {
        "input": "ZeroDivisionError: division by zero",
        "output": """
Classification: ZeroDivisionError

Explanation:
The program attempted to divide by zero.

Likely cause:
The denominator was zero.

Debugging:
Check the denominator before division.

Verification:
Test with zero and non-zero denominators.
"""
    },
    {
        "input": "ModuleNotFoundError: No module named 'pandas'",
        "output": """
Classification: ModuleNotFoundError

Explanation:
Python could not locate the pandas module.

Likely cause:
The package may not be installed in the active Python environment.

Debugging:
Check the active environment and package installation.

Verification:
Import pandas again in the same environment.
"""
    },
    {
        "input": 'TypeError: can only concatenate str (not "int") to str',
        "output": """
Classification: TypeError

Explanation:
A string and an integer are being concatenated.

Likely cause:
Incompatible data types.

Debugging:
Inspect variable types and convert appropriately.

Verification:
Repeat the operation with compatible types.
"""
    }
]


# 4. Define a new error for analysis
new_error = """
Traceback (most recent call last):
  File "app.py", line 12, in <module>
    config = {"debug": True}
TypeError: 'list' object does not support item assignment
"""


# 5. Build the few-shot prompt
prompt_parts = [
    """
You are analyzing software errors.
Learn the expected report structure from the following examples.

Use the examples to understand the expected format.
Do not copy their diagnoses into the new error analysis.
"""
]


# Add each example to the prompt
for index, example in enumerate(examples, start=1):

    example_text = f"""
EXAMPLE {index}

INPUT:
{example['input']}

EXPECTED OUTPUT:
{example['output']}
"""

    prompt_parts.append(example_text)


# Add the new error and analysis instructions
new_error_prompt = f"""
Now analyze this NEW error.

NEW INPUT:
{new_error}

Use the same report structure, but diagnose this error independently.

Provide:

1. Error classification.
2. Simple explanation.
3. Likely root cause.
4. Evidence from the supplied input.
5. Recommended debugging steps.
6. Possible fixes.
7. Verification steps.

Important rules:
- Do not invent missing information.
- Distinguish observed facts from hypotheses.
- Clearly communicate uncertainty.
- Do not claim to have executed the code.
"""

prompt_parts.append(new_error_prompt)


# Combine all prompt sections
few_shot_prompt = "\n".join(prompt_parts)


# 6. Send request to Gemini
response = client.models.generate_content(
    model=model,
    contents=few_shot_prompt,
    config=types.GenerateContentConfig(
        system_instruction=TRACEPILOT_SYSTEM_PROMPT
    )
)


# 7. Display result
print("\nFEW-SHOT DEBUGGING EXPERIMENT")
print("=" * 55)
print(response.text)
