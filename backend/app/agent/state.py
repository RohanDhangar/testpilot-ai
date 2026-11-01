def create_initial_state(url: str, requirement: str) -> dict:
    return {
        "task": {
            "url": url,
            "requirement": requirement,
            "test_steps": [],
            "expected_result": "",
        },

        "browser": {
            "current_url": url,
            "current_title": "",
            "current_snapshot": "",
        },

        "exploration": {
            "visited_pages": [],
            "page_history": [],
        },

        "selectors": [],

        "action_history": [],

        "decision": {},

        "control": {
            "status": "started",
            "current_step_index": 0,
            "iteration_count": 0,
            "max_iteration_count": 20,
            "error": None,
        },

        "generation": {
            "generated_code": "",
        },

        "validation": {
            "status": "pending",
            "errors": [],
        },
    }
