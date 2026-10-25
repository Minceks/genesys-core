"""Bounded, labeled viewport samples for whole-page design judgment."""
import base64


def capture_design_sheet(page):
    """Keep text readable without sending a very tall page as a tiny thumbnail.

    Sample up to three scroll positions without clicking controls or changing routes.
    Compose them on an isolated browser page, using only in-memory screenshots.
    """
    viewport = page.viewport_size
    if not viewport:
        raise ValueError('Design capture requires a bounded viewport')
    width, height = viewport['width'], viewport['height']
    original = page.evaluate('() => ({x: scrollX, y: scrollY})')
    maximum = page.evaluate('() => Math.max(0, document.documentElement.scrollHeight - innerHeight)')
    positions = [0]
    if maximum > height * .25:
        positions.append(min(height, maximum))
    if maximum > height * 1.25:
        positions.append(min(maximum, max(height * 2, round(maximum * .65))))
    samples, panels = [], []
    sheet_context = None
    try:
        for position in dict.fromkeys(positions):
            page.evaluate('(y) => scrollTo({top:y,left:0,behavior:"instant"})', position)
            page.wait_for_timeout(150)
            actual = page.evaluate('() => Math.round(scrollY)')
            if any(sample['scrollY'] == actual for sample in samples):
                continue
            # Decode images exposed by scrolling, including lazy-loaded assets.
            page.evaluate('''async () => { await Promise.race([
                Promise.all([...document.images].filter(img => {
                  const r=img.getBoundingClientRect(); return r.bottom>0 && r.top<innerHeight;
                }).map(img=>img.decode().catch(()=>{}))),
                new Promise(resolve=>setTimeout(resolve,1500))]); }''')
            data = page.screenshot(type='jpeg', quality=70, full_page=False, animations='disabled')
            samples.append({'scrollY': actual, 'width': width, 'height': height})
            panels.append('<div style="height:24px;background:#172630;color:white;font:12px/24px sans-serif;padding-left:8px">'
                          + f'Viewport {width} x {height} | scroll y={actual} | sampled view</div>'
                          + '<img style="display:block;width:100%" src="data:image/jpeg;base64,'
                          + base64.b64encode(data).decode('ascii') + '">')
        sheet_context = page.context.browser.new_context(
            viewport={'width': width, 'height': (height + 24) * len(panels)})
        sheet = sheet_context.new_page()
        sheet.set_content('<html><body style="margin:0">' + ''.join(panels) + '</body></html>')
        sheet.locator('img').evaluate_all('(imgs) => Promise.all(imgs.map(img=>img.decode()))')
        for quality in (70, 45, 25):
            data = sheet.screenshot(type='jpeg', quality=quality, animations='disabled')
            if len(data) <= 2_000_000:
                return data, samples
        raise ValueError('Design contact sheet exceeds bounded image allowance')
    finally:
        if sheet_context:
            sheet_context.close()
        page.evaluate('(p) => scrollTo({top:p.y,left:p.x,behavior:"instant"})', original)
