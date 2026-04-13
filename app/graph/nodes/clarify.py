from __future__ import annotations


def clarify_scope(state: dict) -> dict:
    request = dict(state["request"])
    if not request.get("scope"):
        request["scope"] = "Investigate the question, collect evidence, and produce a cited markdown report."
    return {"request": request}

