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


def test_overflow_evidence_identifies_ancestor_without_waiving_failure():
    result = assess_visual_quality([snapshot(overflow=True, overflowElements=[{
        'tag': 'MAIN', 'class': 'page', 'width': 515, 'parentWidth': 390, 'parentDisplay': 'flex'}])])
    assert result['status'] == 'error'
    assert any('MAIN' in text and '515px' in text and '390px' in text for text in result['suggestions'])


def test_starter_page_cannot_pass():
    assert assess_visual_quality([snapshot(starterVisible=True)])['status'] == 'error'


def test_favicon_cannot_stand_in_for_public_product_artwork():
    data=snapshot(brandVisual=True,favicon=True,titleSize=48,
                  faviconSubjects=[{'alt':'Emergency kit','class':'card-image'}])
    result=assess_visual_quality([data],public_website=True)
    assert any('favicon is reused' in issue for issue in result['issues'])


def test_empty_page_fails_but_graphics_app_can_pass():
    assert assess_visual_quality([snapshot(textLength=0, controls=0)])['status'] == 'error'
    assert assess_visual_quality([snapshot(textLength=0, controls=0, hasGraphics=True)])['status'] == 'success'


def test_readability_and_touch_suggestions_do_not_fake_a_functional_failure():
    result = assess_visual_quality([snapshot(smallTargets=[{'label': 'Save', 'tag': 'BUTTON'}], smallBodyText=2, longLines=1)])
    assert result['status'] == 'success'
    assert len(result['suggestions']) == 3
    assert any('Save' in item for item in result['suggestions'])
