"""Separate executable results from review work and integration scope."""
import re


def verification_report(quality, content, specification=None):
    requirements = (specification or {}).get('requirements', [])
    visual = [r['name'] for r in requirements if r.get('scope') == 'visual']
    external = [r['name'] for r in requirements if r.get('scope') == 'external']
    limitations = []
    for item in content.get('unverified', []):
        if item in content.get('unverifiedCore', []):
            continue
        if any(item.startswith(name + ':') for name in visual + external):
            continue
        if item.startswith('Visual review and real payment processing are '):
            external.append('Real payment processing is deferred; checkout records a local pending order.')
            continue
        limitations.append(item)
    unique = lambda items: list(dict.fromkeys(str(item) for item in items if item))
    return {
        'passed': unique((['Desktop and mobile layout'] if quality.get('status') == 'success' else [])
                         + content.get('testedInteractions', [])),
        'failed': unique(quality.get('issues', []) + content.get('issues', [])),
        'incomplete': unique(content.get('unverifiedCore', [])),
        'manualReview': unique(visual + quality.get('suggestions', [])),
        'deferred': unique(external),
        'limitations': unique(limitations + ['Checks cover the listed workflows; real multi-user behavior was not tested.']),
        # Retain the legacy API field for older clients.
        'unverified': content.get('unverified', []),
        'coverage': content.get('coverage', {}),
        **({'referenceComparison':quality['referenceComparison']} if quality.get('referenceComparison') else {}),
        **({'visualReview':quality['visualReview']} if quality.get('visualReview') else {}),
        **({'workflowVisualReview':quality['workflowVisualReview']} if quality.get('workflowVisualReview') else {}),
        **({'workflowDesignEvidence':content['workflowDesignEvidence']} if content.get('workflowDesignEvidence') else {}),
    }


def strip_legacy_summary(text):
    """Structured report replaces the old trailing chat summary."""
    if not isinstance(text, str):
        return text
    return re.split(r'(?im)^[ \t]*(?:\*\*|#{1,6}[ \t]*)?Verification results(?:\*\*)?[ \t]*:?[ \t]*$', text, maxsplit=1)[0].rstrip()


def finalize_report(result):
    report = result.get('verification')
    if not isinstance(report, dict) or 'manualReview' not in report:
        return
    # A later runtime/preview step may fail after interaction checks passed.
    # Retain partial evidence without displaying an all-clear report.
    if not result.get('browserVerified') and not (report.get('failed') or report.get('incomplete')):
        report['incomplete'] = [result.get('message') or 'Browser verification did not complete.']
    result['text'] = strip_legacy_summary(result.get('text')) or result.get('message') or 'Build checks completed.'
