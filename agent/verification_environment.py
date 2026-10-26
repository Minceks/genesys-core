"""Reversible media emulation and read-only computed-style assertions."""
STYLES=['animation-name','animation-duration','animation-play-state','transition-duration',
        'display','visibility','opacity','color','background-color','font-size','min-height']


def validate_media(step):
    keys={'reducedMotion':{'reduce','no-preference'},'colorScheme':{'light','dark'}}
    if not any(step.get(key) is not None for key in keys):raise ValueError('Invalid verification plan: media preference required')
    for key,allowed in keys.items():
        if step.get(key) is not None and (not isinstance(step[key],str) or step[key] not in allowed):
            raise ValueError('Invalid verification plan: unsupported media preference')


def media_state(page):
    data=page.evaluate('''() => ({reducedMotion:matchMedia('(prefers-reduced-motion:reduce)').matches?'reduce':'no-preference',
        colorScheme:matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light'})''')
    return {'reduced_motion':data.get('reducedMotion','no-preference'),'color_scheme':data.get('colorScheme','light')}


def emulate_media(page,step):
    validate_media(step)
    values={py:step[key] for key,py in [('reducedMotion','reduced_motion'),('colorScheme','color_scheme')] if step.get(key) is not None}
    page.emulate_media(**values)
