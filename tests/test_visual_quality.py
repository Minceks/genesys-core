from agent.visual_quality import assess_visual_quality


def snapshot(**changes):
    result = dict(width=390, overflow=False, controls=3, styledControls=3,
                  composedLayout=True, customBackground=True, textLength=150,
                  hasGraphics=False, starterVisible=False, headings=['Reading Nook'])
    result.update(changes)
    return result


def test_styled_application_passes():
    assert assess_visual_quality([snapshot()])['status'] == 'success'


def test_browser_default_controls_fail():
    result = assess_visual_quality([snapshot(styledControls=0)])
    assert result['status'] == 'error'
    assert 'browser-default' in result['issues'][0]


def test_explicit_unstyled_preference_is_respected():
    assert assess_visual_quality([snapshot(styledControls=0)], allow_unstyled=True)['status'] == 'success'


def test_mobile_overflow_fails_even_for_unstyled_preference():
    assert assess_visual_quality([snapshot(overflow=True)], allow_unstyled=True)['status'] == 'error'


def test_starter_page_cannot_pass():
    assert assess_visual_quality([snapshot(starterVisible=True)])['status'] == 'error'


def test_empty_page_fails_but_graphics_app_can_pass():
    assert assess_visual_quality([snapshot(textLength=0, controls=0)])['status'] == 'error'
    assert assess_visual_quality([snapshot(textLength=0, controls=0, hasGraphics=True)])['status'] == 'success'
