"""Resolve bounded calendar tokens against the browser's local date."""
import re

TOKEN = re.compile(r'\{\{date\+(\d{1,2})\}\}')


def calendar_value(scope, value):
    if not isinstance(value, str) or '{{date' not in value:
        return value
    tokens = TOKEN.findall(value)
    if not tokens or any(int(offset) > 30 for offset in tokens) or '{{date' in TOKEN.sub('', value):
        raise ValueError('Invalid verification plan: date tokens must use {{date+0}} through {{date+30}}')
    page = getattr(scope, 'page', scope)
    def resolve(match):
        return page.evaluate('''offset => {
            const now = new Date();
            const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() + offset);
            return [d.getFullYear(), String(d.getMonth()+1).padStart(2,'0'), String(d.getDate()).padStart(2,'0')].join('-');
        }''', int(match.group(1)))
    return TOKEN.sub(resolve, value)
