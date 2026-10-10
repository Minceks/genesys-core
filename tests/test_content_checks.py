from agent.content_checks import explicit_text_requirements, verify_content


def test_remove_button_can_include_the_book_title_in_accessible_name():
    from playwright.sync_api import sync_playwright
    html = '''<label>Book title<input id="title"></label><button onclick="add()">Add book</button><ul id="books"></ul>
    <script>
    let books = JSON.parse(localStorage.getItem('user-app:v1:books') || '[]');
    function render() { document.getElementById('books').innerHTML = books.map(title => `<li><span>${title}</span><button aria-label="Remove ${title}" onclick="remove()">Remove</button></li>`).join(''); }
    function add() { books.push(document.getElementById('title').value); localStorage.setItem('user-app:v1:books', JSON.stringify(books)); render(); }
    function remove() { books = []; localStorage.setItem('user-app:v1:books', JSON.stringify(books)); render(); }
    render();
    </script>'''
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.route('http://app.test/**', lambda route: route.fulfill(body=html, content_type='text/html'))
        page.goto('http://app.test/')
        result = verify_content(page, 'Build a reading tracker with add and remove book behavior.')
        assert result['status'] == 'success'
        assert result['testedInteractions'] == ['add book', 'refresh persistence', 'remove book']
        browser.close()


def test_explicit_heading_and_button():
    result = explicit_text_requirements('Heading: Reading Nook. Button: Add book.')
    assert result == [{'text': 'Reading Nook', 'unique': True}, {'text': 'Add book', 'unique': False}]


def test_followup_subtitle_literal():
    assert explicit_text_requirements('Add the visible subtitle My reading collection directly beneath Reading Nook.') == [
        {'text': 'My reading collection', 'unique': True}]


def test_generic_request_does_not_invent_expected_text():
    assert explicit_text_requirements('Build a portfolio with a heading and a subtitle.') == []
