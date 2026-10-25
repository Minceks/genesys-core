"""Replay reviewed declarative checks only for the matching request and build."""
import hashlib
import json
from types import SimpleNamespace

PATH = '.genesys-verification-plan.json'


def contract_hash(contract):
    return hashlib.sha256(json.dumps(contract, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def saved_plan_record(prompt, fingerprint, plan, contract):
    return {'version': 2, 'requestHash': hashlib.sha256(prompt.encode()).hexdigest(),
            'buildFingerprint': fingerprint, 'contractHash': contract_hash(contract), 'plan': plan}


def matching_plan(saved, prompt, fingerprint, contract=None):
    if not isinstance(saved, dict) or saved.get('version') not in {1, 2}:
        return None
    if saved['version'] == 2:
        if saved.get('contractHash') != contract_hash(contract):
            return None
    elif contract is not None:
        # Legacy manually reviewed records did not pin the requirements contract.
        return None
    if saved.get('requestHash') != hashlib.sha256(prompt.encode()).hexdigest():
        return None
    if saved.get('buildFingerprint') != fingerprint:
        return None
    plan = saved.get('plan')
    return plan if isinstance(plan, dict) and isinstance(plan.get('checks'), list) else None


class SavedPlanProvider:
    def __init__(self, plan, fallback):
        self.plan = plan
        self.fallback = fallback
        self.replayed = False

    def generate(self, messages, tools):
        system = messages[0].get('content', '') if messages else ''
        if system.startswith('You are a browser verification planner.') and not self.replayed:
            self.replayed = True
            return SimpleNamespace(text=json.dumps(self.plan))
        return self.fallback.generate(messages, tools)
