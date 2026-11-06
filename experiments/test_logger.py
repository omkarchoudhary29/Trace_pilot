
from app.llm.logger import get_logger

logger = get_logger("TracePilot.Test")

logger.info("Logger test started.")
logger.warning("This is a sample warning.")
logger.error("This is a sample error.")

print("\nLogger test completed.")
print("Check logs/tracepilot.log")
