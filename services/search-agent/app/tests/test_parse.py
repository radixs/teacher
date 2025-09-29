from app.clients.duckduckgo import parse_results


def test_parse_results_extracts_entries():
    html = """
    <div class="result">
      <a class="result__a" href="https://example.com">Example Title</a>
      <a class="result__snippet">This is a snippet.</a>
    </div>
    """
    results = parse_results(html)
    assert len(results) == 1
    assert results[0]["title"] == "Example Title"
    assert results[0]["url"] == "https://example.com"
    assert results[0]["snippet"] == "This is a snippet."
