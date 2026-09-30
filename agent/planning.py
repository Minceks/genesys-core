from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlanStep:
    step_id: str
    objective: str
    depends_on: list[str] = field(default_factory=list)
    status: str = "pending"
    actions: list[dict[str, Any]] = field(default_factory=list)
    verification: dict[str, Any] | None = None
    recovery: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "stepId": self.step_id,
            "objective": self.objective,
            "dependsOn": list(self.depends_on),
            "status": self.status,
            "actions": list(self.actions),
            "verification": self.verification,
            "recovery": self.recovery,
        }


@dataclass
class ExecutionPlan:
    objective: str
    steps: list[PlanStep] = field(default_factory=list)
    status: str = "pending"
    current_step_id: str | None = None
    final_verification: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective": self.objective,
            "steps": [step.to_dict() for step in self.steps],
            "status": self.status,
            "currentStepId": self.current_step_id,
            "finalVerification": self.final_verification,
        }

    def get_step(self, step_id: str) -> PlanStep | None:
        for step in self.steps:
            if step.step_id == step_id:
                return step

        return None

    def next_pending_step(self) -> PlanStep | None:
        completed = {
            step.step_id
            for step in self.steps
            if step.status == "completed"
        }

        for step in self.steps:
            if step.status != "pending":
                continue

            if all(
                dependency in completed
                for dependency in step.depends_on
            ):
                return step

        return None

    def is_complete(self) -> bool:
        return bool(self.steps) and all(
            step.status == "completed"
            for step in self.steps
        )

    def has_failed(self) -> bool:
        return any(
            step.status == "failed"
            for step in self.steps
        )


def _extract_plan_payload(response: Any) -> dict[str, Any]:
    if isinstance(response, dict):
        return response

    content = getattr(response, "content", None)

    if isinstance(content, dict):
        return content

    if not isinstance(content, str):
        if isinstance(response, str):
            content = response
        else:
            raise ValueError(
                "Planning response must contain a JSON object."
            )

    content = content.strip()

    if content.startswith("```"):
        lines = content.splitlines()

        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        content = "\n".join(lines).strip()

    if content.lower().startswith("json"):
        content = content[4:].strip()

    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Planning response is not valid JSON."
        ) from exc

    if not isinstance(payload, dict):
        raise ValueError(
            "Planning response must be a JSON object."
        )

    return payload


def build_execution_plan(
    objective: str,
    response: Any,
) -> ExecutionPlan:
    if not isinstance(objective, str) or not objective.strip():
        raise ValueError(
            "Planning objective cannot be empty."
        )

    payload = _extract_plan_payload(response)

    raw_steps = payload.get("steps")

    if not isinstance(raw_steps, list) or not raw_steps:
        raise ValueError(
            "Execution plan must contain at least one step."
        )

    steps: list[PlanStep] = []
    step_ids: set[str] = set()

    for raw_step in raw_steps:
        if not isinstance(raw_step, dict):
            raise ValueError(
                "Each plan step must be an object."
            )

        step_id = raw_step.get("stepId")

        if not isinstance(step_id, str) or not step_id.strip():
            raise ValueError(
                "Each plan step requires a non-empty stepId."
            )

        if step_id in step_ids:
            raise ValueError(
                f"Duplicate plan step ID: {step_id}"
            )

        step_ids.add(step_id)

        step_objective = raw_step.get("objective")

        if (
            not isinstance(step_objective, str)
            or not step_objective.strip()
        ):
            raise ValueError(
                f"Step {step_id} requires a non-empty objective."
            )

        depends_on = raw_step.get("dependsOn", [])

        if isinstance(depends_on, str):
            depends_on = [depends_on]

        if not isinstance(depends_on, list):
            raise ValueError(
                f"Step {step_id} dependsOn must be a list."
            )

        for dependency in depends_on:
            if not isinstance(dependency, str):
                raise ValueError(
                    f"Step {step_id} dependencies must be strings."
                )

        actions = raw_step.get("actions", [])

        if not isinstance(actions, list):
            raise ValueError(
                f"Step {step_id} actions must be a list."
            )

        steps.append(
            PlanStep(
                step_id=step_id,
                objective=step_objective,
                depends_on=list(depends_on),
                actions=list(actions),
            )
        )

    plan = ExecutionPlan(
        objective=objective,
        steps=steps,
    )

    _validate_plan_dependencies(plan)

    return plan


def _validate_plan_dependencies(
    plan: ExecutionPlan,
) -> None:
    step_ids = {
        step.step_id
        for step in plan.steps
    }

    for step in plan.steps:
        for dependency in step.depends_on:
            if dependency not in step_ids:
                raise ValueError(
                    f"Step {step.step_id} has unknown dependencies: "
                    f"{dependency}"
                )

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(step_id: str) -> None:
        if step_id in visiting:
            raise ValueError(
                "Circular plan dependency detected."
            )

        if step_id in visited:
            return

        visiting.add(step_id)

        step = plan.get_step(step_id)

        if step is not None:
            for dependency in step.depends_on:
                visit(dependency)

        visiting.remove(step_id)
        visited.add(step_id)

    for step in plan.steps:
        visit(step.step_id)


def build_planning_prompt(objective: str) -> str:
    if not isinstance(objective, str) or not objective.strip():
        raise ValueError("Planning objective cannot be empty.")

    return f"""
Create an execution plan for the following objective:

{objective}

Return ONLY valid JSON.

The JSON must have this structure:

{{
  "steps": [
    {{
      "stepId": "step-1",
      "objective": "Short description of the step",
      "dependsOn": [],
      "actions": []
    }}
  ]
}}

Requirements:
- Each step must have a unique stepId.
- Each step must have a clear objective.
- dependsOn must contain only step IDs.
- Dependencies must not form cycles.
- actions must be a JSON list.
- Order steps according to their dependencies.
- Do not execute tools.
- Do not include markdown.
- Do not include explanations outside the JSON object.
""".strip()


def execute_plan(
    plan: ExecutionPlan,
    action_executor: Any,
    verifier: Any | None = None,
    recovery_handler: Any | None = None,
    final_verifier: Any | None = None,
) -> ExecutionPlan:
    if not plan.steps:
        raise ValueError("Cannot execute an empty plan.")

    plan.status = "running"

    while True:
        step = plan.next_pending_step()

        if step is None:
            if plan.is_complete():
                if final_verifier is None:
                    plan.status = "completed"
                    plan.current_step_id = None
                    return plan

                try:
                    final_verification_result = final_verifier(plan)
                except Exception as exc:
                    plan.status = "failed"
                    plan.current_step_id = None
                    plan.final_verification = {
                        "status": "error",
                        "message": str(exc),
                    }
                    return plan

                plan.final_verification = final_verification_result

                if not _action_succeeded(
                    final_verification_result
                ):
                    plan.status = "failed"
                    plan.current_step_id = None
                    return plan

                plan.status = "completed"
                plan.current_step_id = None
                return plan

            if plan.has_failed():
                plan.status = "failed"
                plan.current_step_id = None
                return plan

            raise ValueError(
                "Plan cannot make progress. "
                "Check step dependencies."
            )

        plan.current_step_id = step.step_id
        step.status = "running"
        step.verification = None
        step.recovery = None

        action_result = _execute_step_action(
            step,
            action_executor,
        )

        if not _action_succeeded(action_result):
            recovered, recovery_result = _attempt_step_recovery(
                step,
                action_result,
                recovery_handler,
            )

            if recovered:
                action_result = recovery_result
            else:
                step.status = "failed"
                plan.status = "failed"
                return plan

        verification_result = _verify_step(
            step,
            action_result,
            verifier,
        )

        if not _action_succeeded(verification_result):
            recovered, recovery_result = _attempt_step_recovery(
                step,
                verification_result,
                recovery_handler,
            )

            if recovered:
                action_result = recovery_result

                verification_result = _verify_step(
                    step,
                    action_result,
                    verifier,
                )

            if not _action_succeeded(verification_result):
                step.status = "failed"
                plan.status = "failed"
                return plan

        step.status = "completed"


def _execute_step_action(
    step: PlanStep,
    action_executor: Any,
) -> Any:
    try:
        return action_executor(step)
    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc),
        }


def _verify_step(
    step: PlanStep,
    action_result: Any,
    verifier: Any | None,
) -> Any:
    if verifier is None:
        verification_result = {
            "status": "success",
        }
    else:
        try:
            verification_result = verifier(
                step,
                action_result,
            )
        except Exception as exc:
            verification_result = {
                "status": "error",
                "message": str(exc),
            }

    step.verification = verification_result

    return verification_result


def _attempt_step_recovery(
    step: PlanStep,
    failure_result: Any,
    recovery_handler: Any | None,
) -> tuple[bool, Any]:
    if recovery_handler is None:
        step.recovery = {
            "status": "unavailable",
            "failure": failure_result,
        }

        if (
            isinstance(failure_result, dict)
            and "message" in failure_result
        ):
            step.recovery["message"] = failure_result["message"]

        return False, failure_result

    try:
        recovery_result = recovery_handler(
            step,
            failure_result,
        )
    except Exception as exc:
        step.recovery = {
            "status": "error",
            "message": str(exc),
            "failure": failure_result,
        }
        return False, failure_result

    if not _action_succeeded(recovery_result):
        step.recovery = {
            "status": "failed",
            "failure": failure_result,
            "result": recovery_result,
        }
        return False, failure_result

    step.recovery = {
        "status": "success",
        "failure": failure_result,
        "result": recovery_result,
    }

    return True, recovery_result


def _action_succeeded(result: Any) -> bool:
    if result is None:
        return False

    if isinstance(result, bool):
        return result

    if isinstance(result, dict):
        return result.get("status") == "success"

    status = getattr(result, "status", None)

    if status is not None:
        return status == "success"

    return bool(result)