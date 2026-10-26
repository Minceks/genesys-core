"""Necessary source-change evidence for UI requests, not aesthetic certification."""
import re
from pathlib import PurePosixPath


def presentation_changed(diff, new_sources=None):
    groups=[]; current=None
    for line in str(diff or '').splitlines():
        if line.startswith('diff --git '):
            parts=line.split()
            current={'path':parts[-1].removeprefix('b/'),'before':[],'after':[]}
            groups.append(current)
        elif current is not None and line.startswith(('+','-')) and not line.startswith(('+++','---')):
            current['after' if line[0]=='+' else 'before'].append(line[1:])
    # Ordinary git diff omits untracked files. Include newly created UI modules
    # explicitly recorded by this request, without staging customer source.
    for path,content in (new_sources or {}).items():
        if isinstance(content,str):groups.append({'path':path,'before':[],'after':content.splitlines()})
    def clean(value):
        value=re.sub(r'/\*.*?\*/|<!--.*?-->', '', value, flags=re.S)
        value=re.sub(r'(?m)^\s*//[^\n]*$', '', value)
        return re.sub(r'\s+', '', value)
    for group in groups:
        path=PurePosixPath(group['path'])
        if (any(part.startswith('.') for part in path.parts)
                or 'favicon' in path.name.casefold() or path.suffix not in {
                    '.css','.scss','.sass','.less','.jsx','.tsx','.js','.ts','.vue','.svelte','.html','.svg'}):continue
        before,after=('\n'.join(group[key]) for key in ('before','after'))
        if path.suffix=='.html':
            def rendered(value):
                # Keep real head styles and stylesheet choices, exclude titles,
                # metadata, favicons and bootstrap script references.
                styles=re.findall(r'<style\b[^>]*>.*?</style>|<link\b(?=[^>]*\brel=["\']stylesheet["\'])[^>]*>',value,re.I|re.S)
                scripts=[script for script in re.findall(r'<script\b[^>]*>.*?</script>',value,re.I|re.S)
                         if re.search(r'\b(?:canvas|ctx|innerHTML|createElement|fillStyle|strokeStyle)\b',script)]
                body=re.sub(r'<head\b[^>]*>.*?</head>', '', value, flags=re.I|re.S)
                body=re.sub(r'<title\b[^>]*>.*?</title>|<script\b[^>]*>.*?</script>|<(?:meta|link)\b[^>]*>', '', body, flags=re.I|re.S)
                return clean('\n'.join(styles+scripts)+body)
            if rendered(before)!=rendered(after) and (rendered(before) or rendered(after)):return True
        elif clean(before)!=clean(after) and (clean(before) or clean(after)):
            if path.suffix in {'.js','.ts'} and not re.search(r'<[A-Za-z]|\b(?:style|theme|color|canvas|ctx|innerHTML|createElement)\b|\.fillStyle|\.strokeStyle',before+after,re.I):continue
            return True
    return False
