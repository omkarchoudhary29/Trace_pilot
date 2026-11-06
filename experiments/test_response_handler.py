
from types import SimpleNamespace

from app.llm.response_handler import extract_response_metadata, extract_response_text

fake_response = SimpleNamespace(
    text="This is a test debugging response.",
    candidates=[
        SimpleNamespace(finish_reason="STOP")
    ],
    usage_metadata=SimpleNamespace(
        prompt_token_count=20,
        candidates_token_count=35,
        total_token_count=55
    )
)

print("RESPONSE HANDLER TEST")
print("=" * 45)

text = extract_response_text(fake_response)
metadata = extract_response_metadata(fake_response)

print("Response:", text)
print("Metadata:", metadata)
