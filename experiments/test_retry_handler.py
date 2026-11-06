
from app.llm.exceptions import APIServiceError
from app.llm.retry_handler import execute_with_retry

attempts = 0


def unstable_function():
    global attempts

    attempts += 1

    print(f"Attempt: {attempts}")

    if attempts < 3:
        raise APIServiceError("Temporary service failure.")

    return "Success after retry!"


result = execute_with_retry(unstable_function)

print("\nRETRY TEST RESULT")
print("=" * 40)
print(result)
