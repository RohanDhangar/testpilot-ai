import json
import logging
from pathlib import Path

from app.integrations.llm_client import llmAnalysis

logger = logging.getLogger(__name__)

PROMPT_FILE = (
    Path(__file__).resolve().parents[2] / "prompts" / "requirement_analysis_v2.txt"
)


def load_analysis_prompt() -> str:
    try:
        return PROMPT_FILE.read_text(encoding="utf-8").strip()

    except OSError as error:
        logger.error("Unable to read Phase 2 prompt: %s", error)
        raise RuntimeError("Phase 2 requirement prompt could not be loaded.") from error


def validate_test_plan(data: dict) -> bool:
    if not isinstance(data, dict):
        return False

    test_steps = data.get("test_steps")

    if not isinstance(test_steps, list) or not test_steps:
        return False

    allowed_actions = {
        "navigate",
        "click",
        "fill",
        "select",
        "wait",
        "verify",
        "done",
    }

    for index, step in enumerate(test_steps, start=1):

        if not isinstance(step, dict):
            return False

        if type(step.get("step_number")) is not int:
            return False

        if step["step_number"] != index:
            return False

        for field in ("step_name", "description", "action"):
            value = step.get(field)

            if not isinstance(value, str) or not value.strip():
                return False

        if step["action"] not in allowed_actions:
            return False

    expected_result = data.get("expected_result")

    if not isinstance(expected_result, str) or not expected_result.strip():
        return False

    return True


async def requirement_analysis_v2(requirement: str) -> dict:
    if not isinstance(requirement, str) or not requirement.strip():
        return {
            "status": "error",
            "message": "Requirement cannot be empty.",
        }

    try:
        system_prompt = load_analysis_prompt()

        combined_prompt = (
            f"{system_prompt}\n\n" f"USER TESTING REQUIREMENT:\n{requirement.strip()}"
        )

        response = await llmAnalysis(combined_prompt)

        if not isinstance(response, dict):
            return {
                "status": "error",
                "message": "LLM client returned an invalid response.",
            }

        if response.get("status") != "success":
            return {
                "status": "error",
                "message": response.get(
                    "message",
                    "Phase 2 requirement analysis failed.",
                ),
            }

        data = response.get("data")

        if isinstance(data, str):
            data = json.loads(data)

        if not validate_test_plan(data):
            return {
                "status": "error",
                "message": "Phase 2 test plan has an invalid structure.",
            }

        return {
            "status": "success",
            "data": data,
        }

    except (RuntimeError, json.JSONDecodeError) as error:
        logger.error(
            "Phase 2 requirement analysis failed: %s",
            error,
        )

        return {
            "status": "error",
            "message": str(error),
        }

    except Exception:
        logger.exception("Unexpected Phase 2 requirement-analysis failure")

        return {
            "status": "error",
            "message": ("Unexpected Phase 2 requirement-analysis failure."),
        }


async def requirement_analysis_node(state: dict) -> dict:
    task = state["task"]
    requirement = task["requirement"]

    result = await requirement_analysis_v2(requirement)

    if result["status"] != "success":
        return {
            "control": {
                **state["control"],
                "status": "failed",
                "error": result["message"],
            }
        }

    test_plan = result["data"]

    updated_task = {
        **task,
        "test_steps": test_plan["test_steps"],
        "expected_result": test_plan["expected_result"],
    }

    logger.info(
        "Requirement analysis completed. Generated %s test steps.",
        len(test_plan["test_steps"]),
    )

    return {
        "task": updated_task,
    }
