
from app.llm.client import create_gemini_client

client = create_gemini_client()

print("Gemini client created successfully.")
print("Client type:", type(client).__name__)
