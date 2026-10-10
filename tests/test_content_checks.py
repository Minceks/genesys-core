from agent.content_checks import explicit_text_requirements


def test_explicit_heading_and_button():
    result = explicit_text_requirements('Heading: Reading Nook. Button: Add book.')
    assert result == [{'text': 'Reading Nook', 'unique': True}, {'text': 'Add book', 'unique': False}]


def test_followup_subtitle_literal():
    assert explicit_text_requirements('Add the visible subtitle My reading collection directly beneath Reading Nook.') == [
        {'text': 'My reading collection', 'unique': True}]


def test_generic_request_does_not_invent_expected_text():
    assert explicit_text_requirements('Build a portfolio with a heading and a subtitle.') == []
