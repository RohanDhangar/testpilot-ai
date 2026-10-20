import ast
import logging

from app.integrations.llm_client import llmAnalysis

logging.basicConfig(level=logging.INFO)


def validate_genrated_code(test_code: str) -> dict:
    if not isinstance(test_code, str) or not test_code.strip():
        return {
            "status": "error",
            "syntax_valid": False,
            "message": "Generated Python code is empty or invalid.",
        }

    try:
        ast.parse(test_code)
    except SyntaxError as error:
        logging.warning(
            "Generated code syntax error at line %s, column %s: %s",
            error.lineno,
            error.offset,
            error.msg,
        )
        return {
            "status": "error",
            "syntax_valid": False,
            "message": error.msg,
            "line": error.lineno,
            "column": error.offset,
        }

    logging.info("Generated Python code passed syntax validation.")
    return {
        "status": "success",
        "syntax_valid": True,
        "message": "Python syntax is valid.",
    }


async def repaire_generated_code(test_code: str, max_attempt: int = 2) -> dict:
    current_code = test_code

    for attempt in range(max_attempt + 1):
        validation = validate_genrated_code(current_code)

        if validation["syntax_valid"]:
            return {
                "status": "success",
                "test_code": current_code,
                "validation": validation,
                "repair_attempts": attempt,
            }

        if attempt == max_attempt:
            break

        repair_prompt = f"""You are repairing Python syntax errors in generated Playwright test code.

Fix ONLY syntax and indentation errors reported by Python.
Preserve the original test intent, URL, selectors, assertions, and behavior.
Do not invent credentials, selectors, or new application behavior.
Return ONLY a JSON object with one key: "test_code".
The value must contain the complete corrected Python source code.
Do not use Markdown fences.

PYTHON PARSER ERROR:

{validation}

CURRENT CODE:

{current_code}
"""

        result = await llmAnalysis(repair_prompt)

        if not isinstance(result, dict) or result.get("status") != "success":
            return {
                "status": "error",
                "message": "LLM syntax repair request failed.",
                "validation": validation,
            }

        repaired_data = result.get("data")

        if not isinstance(repaired_data, dict) or not isinstance(repaired_data.get("test_code"), str):
            return{
                "status": "error",
                "message": "LLM returned an invalid repair response.",
            }

        current_code = repaired_data["test_code"]

    return{
        "status": "error",
        "message": "Generated code still has syntax errors after repair attempts.",
        "test_code": current_code,
        "validation": validate_genrated_code(current_code),
        "repair_attempts": max_attempt,
    }
