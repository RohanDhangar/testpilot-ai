import json
import logging
from pathlib import Path

from app.services.code_validation import repaire_generated_code
from app.integrations.llm_client import llmAnalysis
from app.integrations.mcp_client import (
    explore_application as fetch_application_snapshot,
)

logging.basicConfig(level=logging.INFO)

PROMPT_FILE = Path(__file__).resolve().parents[2] / "prompts" / "code_generation.txt"


def load_code_genration_prompt() -> str:
    try:
        return PROMPT_FILE.read_text(encoding="utf-8").strip()
    except OSError as error:
        logging.exception(f"Failed to load code generation prompt: {error}")
        raise RuntimeError("Could not load prompts/code_generation.txt.") from error


async def code_genration(url: str, analysis_data: dict) -> dict:
    if not isinstance(url, str) or not url.strip():
        return {"status": "error", "message": "A valid application URL is required."}

    if not isinstance(analysis_data, dict) or analysis_data.get("status") != "success":
        return {
            "status": "error",
            "message": "A successful requirement-analysis result is required",
        }

    test_plan = analysis_data.get("data")

    if not isinstance(test_plan, dict):
        return {
            "status": "error",
            "message": "Requirement-analysis data must be a JSON object.",
        }

    try:
        system_prompt = load_code_genration_prompt()
        browser_result = await fetch_application_snapshot(url.strip())

        if (
            not isinstance(browser_result, dict)
            or browser_result.get("status") != "success"
        ):
            return {
                "status": "error",
                "message": "Application exploration failed.",
                "details": browser_result,
            }

        snapshot = browser_result.get("snapshot")

        if not isinstance(snapshot, str) or not snapshot.strip():
            return {
                "status": "error",
                "message": "The application snapshot is empty or invalid.",
            }

        combined_prompt = (
            f"{system_prompt} \n \n"
            "application URL \n"
            f"{url.strip()} \n \n"
            "Requirement analysis JSON: \n"
            f"{json.dumps(test_plan, ensure_ascii=False, indent=2)}\n \n"
            "Playwright MCP page snapshot: \n"
            f"{snapshot}\n \n"
        )

        llm_result = await llmAnalysis(combined_prompt)

        if not isinstance(llm_result, dict) or llm_result.get("status") != "success":
            return {
                "status": "error",
                "message": "Code generation failed.",
                "details": llm_result,
            }

        genrated_data = llm_result.get("data")

        if not isinstance(genrated_data, dict) or not isinstance(
            genrated_data.get("test_code"), str
        ):
            return {
                "status": "error",
                "message": "Gemini returned an invalid code-generation structure.",
            }

        validation_result = await repaire_generated_code(genrated_data["test_code"])

        if validation_result.get("status") != "success":
            return {
                "status": "error",
                "message": "Generated code could not pass syntax validation.",
                "validation": validation_result,
                "generated": genrated_data,
                "url": url.strip(),
            }

        genrated_data["test_code"] = validation_result["test_code"]

        logging.info("Playwright test-code generation completed.")
        return {
            "status": "success",
            "url": url.strip(),
            "test_plan": test_plan,
            "snapshot": snapshot,
            "generated": genrated_data,
            "validation": validation_result,
        }

    except RuntimeError as error:
        logging.error("Code-generation setup failed: %s", error)
        return {"status": "error", "message": str(error)}

    except Exception:
        logging.error("unexpected code genration failed")
        return {
            "status": "error",
            "message": "Unexpected error during code generation. Check the logs.",
        }
