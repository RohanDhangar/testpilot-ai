import json
import logging
import re
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import StateGraph, END

from app.integrations.llm_client import llmAnalysis

logger = logging.getLogger(__name__)

PROMPT_FILE = (
    Path(__file__).resolve().parents[2] / "prompts" / "exploration_decision.txt"
)


class ExplorationState(TypedDict, total=False):
    task: dict
    browser: dict
    exploration: dict
    selectors: list
    action_history: list
    control: dict
    decision: dict


def load_decision_prompt() -> str:
    try:
        return PROMPT_FILE.read_text(encoding="utf-8").strip()
    except OSError as error:
        logger.error("Unable to load exploration prompt: %s", error)
        raise RuntimeError(
            "Exploration decision prompt could not be loaded."
        ) from error


def get_mcp_client(config: dict):
    client = config.get("configurable", {}).get("mcp_client")

    if client is None:
        raise RuntimeError("Persistent MCP client was not provided.")

    return client


def extract_page_details(snapshot: str) -> tuple[str, str]:
    url_match = re.search(r"Page URL:\s*(.+)", snapshot)
    title_match = re.search(r"Page Title:\s*(.+)", snapshot)

    current_url = url_match.group(1).strip() if url_match else ""
    current_title = title_match.group(1).strip() if title_match else ""

    return current_url, current_title


def validate_decision(decision: Any) -> bool:
    if not isinstance(decision, dict):
        return False

    action = decision.get("action")

    if action not in {
        "navigate",
        "click",
        "fill",
        "wait",
        "done",
        "blocked",
    }:
        return False

    if not isinstance(decision.get("reason"), str):
        return False

    if action == "navigate":
        return isinstance(decision.get("url"), str) and bool(decision["url"].strip())

    if action == "click":
        return isinstance(decision.get("target"), str) and bool(
            decision["target"].strip()
        )

    if action == "fill":
        has_target = isinstance(decision.get("target"), str) and bool(
            decision["target"].strip()
        )

        has_text = isinstance(decision.get("text"), str)
        has_secret = isinstance(decision.get("secret_key"), str)

        return has_target and (has_text != has_secret)

    if action == "wait":
        return isinstance(decision.get("text"), str) and bool(decision["text"].strip())

    return True


async def snapshot_node(
    state: ExplorationState,
    config: dict,
) -> dict:
    logger.info("Exploration: capturing current page snapshot.")

    client = get_mcp_client(config)
    browser = state.get("browser", {})

    # Navigate to the application only once at the beginning.
    if not browser.get("initial_navigation_done"):
        navigation = await client.navigate(state["task"]["url"])

        if navigation.get("status") != "success":
            return {
                "control": {
                    **state.get("control", {}),
                    "status": "error",
                    "error": navigation.get("message", "Initial navigation failed."),
                }
            }

        browser = {
            **browser,
            "initial_navigation_done": True,
        }

    result = await client.snapshot()

    if result.get("status") != "success":
        return {
            "browser": browser,
            "control": {
                **state.get("control", {}),
                "status": "error",
                "error": result.get("message", "Snapshot failed."),
            },
        }

    snapshot = result.get("result", "")
    current_url, current_title = extract_page_details(snapshot)

    page_history = state.get("exploration", {}).get("page_history", [])

    updated_history = [
        *page_history,
        {
            "url": current_url,
            "title": current_title,
            "snapshot": snapshot,
        },
    ]

    return {
        "browser": {
            **browser,
            "current_url": current_url,
            "current_title": current_title,
            "current_snapshot": snapshot,
        },
        "exploration": {
            **state.get("exploration", {}),
            "page_history": updated_history,
        },
    }


async def decision_node(
    state: ExplorationState,
    config: dict,
) -> dict:
    logger.info("Exploration: asking Gemini for the next action.")

    prompt_template = load_decision_prompt()

    decision_context = {
        "task": state.get("task", {}),
        "current_browser": {
            "url": state.get("browser", {}).get("current_url", ""),
            "title": state.get("browser", {}).get("current_title", ""),
            "snapshot": state.get("browser", {}).get("current_snapshot", ""),
        },
        "action_history": state.get("action_history", []),
        "current_step_index": state.get("control", {}).get("current_step_index", 0),
        "iteration_count": state.get("control", {}).get("iteration_count", 0),
    }

    combined_prompt = (
        f"{prompt_template}\n\n"
        "CURRENT EXPLORATION CONTEXT:\n"
        f"{json.dumps(decision_context, ensure_ascii=False)}"
    )

    response = await llmAnalysis(combined_prompt)

    if response.get("status") != "success":
        return {
            "control": {
                **state.get("control", {}),
                "status": "error",
                "error": response.get("message", "Gemini decision failed."),
            }
        }

    decision = response.get("data")

    if isinstance(decision, str):
        try:
            decision = json.loads(decision)
        except json.JSONDecodeError:
            decision = None

    if not validate_decision(decision):
        return {
            "control": {
                **state.get("control", {}),
                "status": "error",
                "error": "Gemini returned an invalid exploration decision.",
            }
        }

    return {"decision": decision}


async def action_node(
    state: ExplorationState,
    config: dict,
) -> dict:
    decision = state.get("decision", {})
    action = decision.get("action")

    logger.info("Exploration: executing action '%s'.", action)

    if action in {"done", "blocked"}:
        status = "completed" if action == "done" else "blocked"

        return {
            "control": {
                **state.get("control", {}),
                "status": status,
            },
            "action_history": [
                *state.get("action_history", []),
                {
                    "action": action,
                    "reason": decision.get("reason", ""),
                },
            ],
        }

    client = get_mcp_client(config)
    secrets = config.get("configurable", {}).get("secrets", {})

    if action == "navigate":
        result = await client.navigate(decision["url"])

    elif action == "click":
        result = await client.click(
            target=decision["target"],
            element=decision.get("element", ""),
        )

    elif action == "fill":
        if "secret_key" in decision:
            secret_key = decision["secret_key"]

            if secret_key not in secrets:
                return {
                    "control": {
                        **state.get("control", {}),
                        "status": "blocked",
                        "error": f"Required secret '{secret_key}' was not provided.",
                    }
                }

            text_to_type = secrets[secret_key]
        else:
            text_to_type = decision["text"]

        result = await client.type_text(
            target=decision["target"],
            text=text_to_type,
            element=decision.get("element", ""),
        )

    elif action == "wait":
        result = await client.call_tool(
            "browser_wait_for",
            {"text": decision["text"]},
        )

    else:
        result = {
            "status": "error",
            "message": f"Unsupported action: {action}",
        }

    action_history = [
        *state.get("action_history", []),
        {
            "action": action,
            "reason": decision.get("reason", ""),
            "target": decision.get("target"),
            "result": result,
        },
    ]

    if result.get("status") != "success":
        return {
            "action_history": action_history,
            "control": {
                **state.get("control", {}),
                "status": "error",
                "error": result.get("message", "Browser action failed."),
            },
        }

    step_completed = decision.get("step_completed", False)
    control = state.get("control", {})

    return {
        "action_history": action_history,
        "control": {
            **control,
            "iteration_count": control.get("iteration_count", 0) + 1,
            "current_step_index": (
                control.get("current_step_index", 0) + 1
                if step_completed
                else control.get("current_step_index", 0)
            ),
        },
    }


def route_after_action(state: ExplorationState) -> str:
    control = state.get("control", {})

    status = control.get("status", "started")
    iteration_count = control.get("iteration_count", 0)
    max_iterations = control.get("max_iteration_count", 20)

    if status != "started":
        return END

    if iteration_count >= max_iterations:
        return END

    return "snapshot"


def build_exploration_graph():
    graph = StateGraph(ExplorationState)

    graph.add_node("snapshot", snapshot_node)
    graph.add_node("decision", decision_node)
    graph.add_node("action", action_node)

    graph.set_entry_point("snapshot")

    graph.add_edge("snapshot", "decision")
    graph.add_edge("decision", "action")

    graph.add_conditional_edges(
        "action",
        route_after_action,
        {
            "snapshot": "snapshot",
            END: END,
        },
    )

    return graph.compile()


exploration_graph = build_exploration_graph()
