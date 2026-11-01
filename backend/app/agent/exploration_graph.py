import json
import logging
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import START, END, StateGraph
from langchain_core.runnables import RunnableConfig

from app.integrations.llm_client import llmAnalysis

logger = logging.getLogger(__name__)

PROMPT_FILE = (
    Path(__file__).resolve().parents[2] / "prompts" / "exploration_decision.txt"
)


class ExplorationState(TypedDict, total=False):
    task: dict
    browser: dict
    exploration: dict
    selectors: dict
    action_history: dict
    control: dict
    decision: dict
    generation: dict
    validation: dict


def load_decision_prompt() -> str:
    try:
        return PROMPT_FILE.read_text(encoding="utf-8").strip()

    except OSError as error:
        logger.error("unable to read the prompt file: %s", error)
        raise RuntimeError(
            "Exploration decision prompt could not be loaded."
        ) from error


def validate_decision(data: dict) -> bool:
    if not isinstance(data, dict):
        return False

    allowed_actions = {
        "navigate",
        "click",
        "fill",
        "select",
        "wait",
        "verify",
        "done",
        "blocked",
    }

    action = data.get("action")

    if action not in allowed_actions:
        return False

    if not isinstance(data.get("step_completed"), bool):
        return False

    if not isinstance(data.get("reason"), str):
        return False

    if action in {"click", "fill", "select"}:
        if isinstance(data.get("target"), str):
            return False

        if not data["target"].strip():
            return False

    if action == "navigate":
        if isinstance(data.get("url"), str):
            return False

        if not data["url"].strip():
            return False

    if action == "fill":
        text = data.get("text", "")
        secret_key = data.get("secret_key", "")

        if not isinstance(text, str):
            return False

        if not isinstance(secret_key, str):
            return False

        if bool(text.strip()) == bool(secret_key.strip()):
            return False

    if action == "select":
        if not isinstance(data.get("option_value"), str):
            return False

        if not data["option_value"].strip():
            return False

    if action == "wait":
        wait_seconds = data.get("wait_seconds")

        if (
            not isinstance(wait_seconds, (int, float))
            or isinstance(wait_seconds, bool)
            or wait_seconds < 0
        ):
            return False

    return True


async def snapshot_node(state: ExplorationState, config: RunnableConfig) -> dict:
    client = config.get("configurable", {}).get("mcp_client")

    if client is None:
        return {
            "control": {
                **state["control"],
                "status": "failed",
                "error": "MCP client was not provided to the graph.",
            }
        }

    browser = state["browser"]
    task = state["task"]

    if not browser.get("current_snapshot"):
        navigation = await client.navigate(task["url"])

        if navigation.get("status") != "success":
            return {
                "control": {
                    **state["control"],
                    "status": "failed",
                    "error": navigation.get(
                        "message",
                        "Initial browser navigation failed.",
                    ),
                }
            }

        browser = {**browser, "current_url": task["url"]}

        ## capturing the page snaphot

        snapshot_result = await client.snapshot()

        if snapshot_result.get("status") != "success":
            return {
                "control": {
                    **state["control"],
                    "status": "failed",
                    "error": snapshot_result.get(
                        "message",
                        "Browser snapshot failed.",
                    ),
                }
            }

        snapshot_text = snapshot_result.get("result", "")

        updated_browser = {**browser, "current_snapshot": snapshot_text}

        exploration = state["exploration"]
        current_url = updated_browser.get("current_url", "")

        visited_pages = list(exploration.get("visited_pages", []))

        if current_url and current_url not in visited_pages:
            visited_pages.append(current_url)

        page_history = list(exploration.get("page_history", []))

        page_history.append(
            {
                "url": current_url,
                "snapshot": snapshot_text,
                "iteration": state["control"].get("iteration_count", 0),
            }
        )

        updated_exploration = {
            **exploration,
            "visited_pages": visited_pages,
            "page_history": page_history,
        }

        logger.info("Browser snapshot captured successfully.")

        return {"browser": updated_browser, "exploration": updated_exploration}


async def decision_node(state: ExplorationState, config: RunnableConfig) -> dict:
    try:
        system_prompt = load_decision_prompt()

        task = state["task"]
        control = state["control"]

        test_steps = task.get("test_steps", [])
        current_index = control.get("current_step_index", 0)

        if current_index >= len(test_steps):
            return {
                "decision": {
                    "action": "done",
                    "step_completed": True,
                    "reason": "All planned test steps are complete.",
                }
            }

        secrets = (
            config.get("configurable", {}).get("secrets", {})
        )

        decision_context = {
            "requirement": task.get("requirement", ""),
            "test_steps": test_steps,
            "current_step_index": current_index,
            "current_step": test_steps[current_index],
            "expected_result": task.get("expected_result", ""),
            "browser_snapshot": state["browser"].get("current_snapshot", ""),
            "current_url": state["browser"].get("current_url", ""),
            "action_history": state.get("action_history", []),
            "available_secret_keys": list(secrets.keys()),
            "iteration_count": control.get("iteration_count", 0),
        }

        combined_prompt = (
            f"{system_prompt} \n \n"
            "Current WorkFlow Context: \n"
            f"{json.dumps(decision_context, ensure_ascii=False)}"
        )

        logger.info("prompt for decision: ", combined_prompt)

        response = await llmAnalysis(combined_prompt)

        if not isinstance(response, dict):
            raise ValueError("LLM returned an invalid response.")

        if response.get("status") != "success":
            raise RuntimeError(
                response.get("message", "LLM decision failed.")
            )

        decision = response.get("data")

        if isinstance(decision, str):
            decision = json.loads(decision)

        if not validate_decision(decision):
            raise ValueError(
                "LLM returned an invalid action decision."
            )

        logger.info("Next action is decided: ", decision["action"])

        return {
            "decision": decision
        }

    except Exception as error:
        logger.exception("Explore the decision failed")

        return {
            "control": {
                **state["control"],
                "status": "failed",
                "error": str(error)
            }
        }

async def action_node(state: ExplorationState, config: RunnableConfig) -> dict:
    