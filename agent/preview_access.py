"""Network access pages are infrastructure failures, never generated-app defects."""


class PreviewAccessBlocked(RuntimeError):
    pass


def check_preview_document(page):
    text=page.locator('body').inner_text(timeout=5000).casefold()
    if (('antivīruss' in text or 'antiviruss' in text) and 'bite.lv' in text
            and ('piekļuve ir ierobežota' in text or 'turpināt' in text)):
        raise PreviewAccessBlocked('The preview reached a network access warning instead of the application. Source is preserved; retry through the configured project preview domain.')
