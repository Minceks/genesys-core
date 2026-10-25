"""Distinguish a whole-product brief from a targeted change without a model call."""
import re


def replaces_product(prompt):
    text = prompt.strip().lower()
    # Quoted examples, questions and feature additions are not replacement consent.
    if re.match(r'^(?:how|why|what|explain|discuss|plan|do not|don.t)\b', text):
        return False
    if re.search(r'\b(?:website|app|store|shop|dashboard)\s+(?:header|footer|button|menu|section|component|widget|page|feature|logo)\b', text):
        return False
    prefix = r'^(?:(?:please|can you|could you|i want you to|i want to|i need you to)\s+)*'
    product = r'(?:website|web\s*site|app|application|store|shop|portfolio|dashboard|game|landing page)\b'
    create = r'(?:build|create|make)\s+(?:me\s+)?(?:a|an|another|new|a new|an entirely new|a completely new)\s+(?:\w+[ -]){0,5}?'
    replace = r'(?:replace|rebuild)\s+(?:(?:this|the|my|existing|current|entire)\s+){0,4}'
    return bool(re.search(prefix + '(?:' + create + product + '|' + replace + product + ')', text))
