from agent.verification_report import verification_report, strip_legacy_summary, finalize_report


def test_review_and_deferred_items_are_separate_from_passed_checks():
    spec = {'requirements': [{'name': 'Review imagery', 'scope': 'visual'},
                             {'name': 'External email delivery', 'scope': 'external'}]}
    report = verification_report({'status': 'success', 'suggestions': ['Enlarge phone controls']},
        {'testedInteractions': ['Cart persistence'], 'unverified': ['Review imagery: long acceptance',
          'External email delivery: long acceptance', 'Visual review and real payment processing are separate from these local browser checks.']}, spec)
    assert report['passed'] == ['Desktop and mobile layout', 'Cart persistence']
    assert not report['failed'] and not report['incomplete']
    assert report['manualReview'] == ['Review imagery', 'Enlarge phone controls']
    assert 'External email delivery' in report['deferred']
    assert any('payment' in item for item in report['deferred'])
    assert all('long acceptance' not in item for item in report['limitations'])


def test_failed_and_incomplete_checks_cannot_be_reclassified_as_deferred():
    report = verification_report({'status': 'error', 'issues': ['Phone overflow']},
        {'issues': ['Wrong subtotal'], 'unverifiedCore': ['Cart persistence not checked'],
         'unverified': ['Cart persistence not checked']})
    assert report['failed'] == ['Phone overflow', 'Wrong subtotal']
    assert report['incomplete'] == ['Cart persistence not checked']
    assert not report['deferred']
    assert 'Cart persistence not checked' not in report['limitations']


def test_only_trailing_legacy_verification_section_is_replaced():
    assert strip_legacy_summary('Updated the cart.\n\n**Verification results**\nPassed: Cart\nUnverified: Review') == 'Updated the cart.'
    assert strip_legacy_summary('Verification results appear in the report.') == 'Verification results appear in the report.'


def test_later_runtime_failure_cannot_display_an_all_clear_report():
    result = {'browserVerified': False, 'message': 'Runtime error after checkout',
              'verification': {'passed': ['Checkout'], 'manualReview': [], 'failed': [], 'incomplete': []}}
    finalize_report(result)
    assert result['verification']['passed'] == ['Checkout']
    assert result['verification']['incomplete'] == ['Runtime error after checkout']
