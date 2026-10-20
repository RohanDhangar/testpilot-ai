from app.integrations.llm_client import llmAnalysis
from pathlib import Path
import logging
import json

logging.basicConfig(level = logging.INFO)

PROMPT_FILE = (
    Path(__file__).resolve().parents[2]
    /"prompts"
    /"requirement_analysis.txt"
)

def load_analysis_prompt() -> str:
    try:
        return PROMPT_FILE.read_text(encoding = "utf-8").strip()
    except OSError as error:
        logging.error(f"Error reading prompt file: {error}")
        raise RuntimeError(f"Error reading prompt file: {error}") from error

def validate_test_plan(data: dict) -> bool:
    if not isinstance(data, dict):
        logging.error("Input data is not a dictionary.")
        return False

    if data.get("error"):
        logging.error(f"Error in input data: {data['error']}")
        return False

    test_steps = data.get("test_steps")
    expected_result = data.get("expected_result")
    required_elements = data.get("required_elements")

    if not isinstance(test_steps, list) or not test_steps:
        logging.error("Test steps must be a non-empty list.")
        return False

    if not all(
        isinstance(step, str) and step.strip()
        for step in test_steps
    ):
        return False

    if not isinstance(expected_result, str) or not expected_result.strip():
        return False
    
    if not isinstance(required_elements, list) or not required_elements:
        logging.error("Required elements must be a non-empty list.")
        return False


    for element in required_elements:
        if not isinstance(element, dict):
            return False

        if not element["name"].strip():
            return False

        if not isinstance(element["purpose"], str) or not element["purpose"].strip():
            return False


    return True

        

async def requirement_analysis(prompt: str) -> dict:
    if not isinstance(prompt, str) or not prompt.strip():
        return {"status": "error", "message": "Prompt cannot be empty.Please provide the valid prompt."}

    try:
        system_prompt = load_analysis_prompt()
        combined_prompt = (
            f"{system_prompt}\n\n"
            "USER TESTING REQUIREMENT:\n"
            f"{prompt.strip()}"
        )

        response = await llmAnalysis(combined_prompt)

        if not isinstance(response, dict):
            return {
                "status": "error",
                "message": "LLM client returned an invalid response."
            }

        if response.get("status") != "success":
            return {
                "status": "error",
                "message": response.get(
                    "message",
                    "Requirement analysis failed."
                )
            }

        data = response.get("data")

        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return {
                    "status": "error",
                    "message": "LLM response is not valid JSON."
                }

        if not validate_test_plan(data):
            return {
                "status": "error",
                "message": "LLM response does not match the test-plan structure."
            }

        return {
            "status": "success",
            "data": data
        }

    except RuntimeError as error:
        logging.error("Requirement analysis setup failed: %s", error)
        return {
            "status": "error",
            "message": str(error)
        }

    except Exception:
        logging.exception("Unexpected requirement-analysis failure")
        return {
            "status": "error",
            "message": "An unexpected error occurred during requirement analysis."
        }