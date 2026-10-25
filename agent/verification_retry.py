"""Preserve executed workflows when a planner repairs a failed sequence."""
from copy import deepcopy


def retain_passed_checks(plan, passed_checks):
    plan = deepcopy(plan)
    checks = plan['checks']
    for passed in passed_checks:
        # Coverage IDs alone are not workflow identity: a requirement may need
        # both successful creation and a separate failing deletion check.
        matches = [i for i, check in enumerate(checks)
                   if isinstance(check, dict) and check.get('name') == passed['name']]
        if len(matches) == 1:
            checks[matches[0]] = deepcopy(passed)
        else:
            checks.append(deepcopy(passed))
    # Existing plan validation enforces the normal step/check budget. Retained
    # checks are executed again against the restored baseline, never pre-passed.
    return plan
