"""E2E coverage for preview-from-url recipe extraction."""

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from app.tests.clients.api_client import APIClient
from app.tests.utils.constants import HTTP_OK, HTTP_UNPROCESSABLE_ENTITY
from app.tests.utils.helpers import maybe_throttle


@contextmanager
def local_recipe_page_server(html: str):
    """Serve a local HTML recipe page for endpoint fetch testing."""

    class _RecipePageHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self.send_response(HTTP_OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            del format, args

    server = ThreadingHTTPServer(("127.0.0.1", 0), _RecipePageHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/recipe"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_preview_from_url_extracts_recipe_preview(api_client: APIClient) -> None:
    recipe_html = """
    <html>
      <body>
        <h1>Lemon Garlic Pasta</h1>
        <p>Servings: 2</p>
        <p>Total time: 20 minutes</p>
        <h2>Ingredients</h2>
        <ul>
          <li>200g spaghetti</li>
          <li>2 cloves garlic</li>
          <li>1 tbsp olive oil</li>
          <li>1 tbsp lemon juice</li>
          <li>1 tsp lemon zest</li>
        </ul>
        <h2>Instructions</h2>
        <ol>
          <li>Boil pasta until al dente.</li>
          <li>Saute garlic in olive oil.</li>
          <li>Toss pasta with lemon juice and zest.</li>
        </ol>
      </body>
    </html>
    """

    with local_recipe_page_server(recipe_html) as source_url:
        maybe_throttle()
        response = api_client.recipes.preview_recipe_from_url(source_url)

    assert response["status_code"] == HTTP_OK
    payload = response["data"]
    assert payload["success"] is True, payload
    assert payload["created"] is False
    assert payload["url"] == source_url
    assert payload["diagnostics"]["raw_html_length"] > 0
    assert payload["diagnostics"]["extracted_text_length"] > 0
    assert payload["diagnostics"]["cleaned_text_length"] > 0
    preview = payload["recipe_preview"]
    assert preview["title"]
    assert isinstance(preview["ingredients"], list)
    assert len(preview["ingredients"]) > 0
    assert isinstance(preview["instructions"], list)
    assert len(preview["instructions"]) > 0


def test_preview_from_url_rejects_invalid_url(api_client: APIClient) -> None:
    response = api_client.recipes.preview_recipe_from_url("not-a-url")
    assert response["status_code"] == HTTP_UNPROCESSABLE_ENTITY
