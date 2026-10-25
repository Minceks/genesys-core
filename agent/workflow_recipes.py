"""Bounded local CRUD/booking recipes; unknown contracts use the AI planner."""
from datetime import date, timedelta
import re


def workflow_plan(page, contract, sources):
    from .functional_verification import target
    def field(label):
        return target(page, {'by': 'label', 'name': label})
    requirements = [item for item in (contract or {}).get('requirements', []) if item.get('scope') == 'browser']
    if len(requirements) != 1:
        return None
    requirement = requirements[0]
    text = requirement.get('name', '') + ' ' + requirement.get('acceptance', '')
    source = '\n'.join((sources or {}).values())
    if 'localStorage' not in source or re.search(r'\bfetch\s*\(|\baxios\b|\bsupabase\b|\bXMLHttpRequest\b', source):
        return None
    if re.search(r'\b(server|sync|account|upload|payment|email delivery|recurring|reminder|export|calendar integration)\b', text, re.I):
        return None
    def action(kind, by=None, name=None, **extra):
        return {'action': kind, **({'target': {'by': by, 'name': name}} if by else {}), **extra}
    def button(name, within=None):
        return {'action': 'click', 'target': {'by': 'role', 'role': 'button', 'name': name,
                                            **({'withinText': within} if within else {})}}
    def visible(name):
        return action('visible', 'text', name)
    marker = 'Genesys verification record 84731'
    if page.get_by_text(marker, exact=False).count():
        return None
    steps = None
    if all(re.search(pattern, text, re.I) for pattern in (r'\b(task|todo)\b', r'\b(create|add)\b', r'\b(delete|remove)\b', r'\b(persist|reload)\b')):
        if re.search(r'\b(priority|due date|assign|sharing|attachment|sorting|filtering|undo)\b', text, re.I):
            return None
        # Explicit recipe markup lets generated implementations expose a stable
        # contract while all outcomes are still proved through real UI actions.
        if 'data-genesys-workflow="tasks"' not in source or not all(word in source for word in ('Delete task', 'Task title')):
            return None
        if page.get_by_label('Task title', exact=True).count() != 1 or page.get_by_role('button', name='Add task', exact=True).count() != 1:
            return None
        steps = [action('type', 'label', 'Task title', value=marker), button('Add task'), visible(marker)]
        final_marker = marker
        if re.search(r'\b(edit|update|crud)\b', text, re.I):
            if not all(word in source for word in ('Edit task', 'Save task', 'Edit task title')):
                return None
            final_marker += ' updated'
            steps += [button('Edit task', marker), action('type', 'label', 'Edit task title', value=final_marker),
                      button('Save task'), visible(final_marker)]
        steps += [action('reload'), visible(final_marker), button('Delete task', final_marker),
                  action('absent', 'text', final_marker), action('reload'), action('absent', 'text', final_marker)]
    elif all(re.search(pattern, text, re.I) for pattern in (r'\b(booking|appointment)\b', r'\b(create|book)\b', r'\bcancel\b', r'\b(persist|reload)\b')):
        if re.search(r'\b(reschedule|edit|update|undo|conflict|capacity|timezone|calendar)\b', text, re.I):
            return None
        if 'data-genesys-workflow="appointments"' not in source or 'Cancel booking' not in source:
            return None
        labels = ('Customer name', 'Appointment date', 'Service', 'Time')
        if any(field(label).count() != 1 for label in labels) or page.get_by_role('button', name='Book appointment', exact=True).count() != 1:
            return None
        date_field = field('Appointment date')
        selected_date = max((date.today() + timedelta(days=7)).isoformat(), date_field.get_attribute('min') or '')
        maximum = date_field.get_attribute('max')
        if maximum and selected_date > maximum:
            return None
        options = {}
        for label in ('Service', 'Time'):
            values = field(label).locator('option').evaluate_all('els => els.filter(e=>!e.disabled&&e.value).map(e=>e.value)')
            if not values:
                return None
            options[label] = values[0]
        steps = [action('type', 'label', 'Customer name', value=marker),
                 action('fill', 'label', 'Appointment date', value=selected_date),
                 action('select', 'label', 'Service', value=options['Service']),
                 action('select', 'label', 'Time', value=options['Time']), button('Book appointment'),
                 visible(marker), action('reload'), visible(marker), button('Cancel booking', marker),
                 action('absent', 'text', marker), action('reload'), action('absent', 'text', marker)]
        for item in steps:
            if item['action'] in {'visible', 'absent'} and item.get('target', {}).get('name') == marker:
                item['target']['exact'] = False  # Booking summaries also include the date/time.
    if steps is None:
        return None
    return {'requirements': requirements, 'checks': [{'name': requirement['name'], 'covers': [requirement['id']],
             'independent': True, 'steps': steps}], 'unverified': [], 'unverifiedCore': [],
             'coreRequestEvidence': [], 'planner': 'observed-local-workflow-v1'}
