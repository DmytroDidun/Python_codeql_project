"""Guestbook web app built with Robyn.

Intentionally vulnerable to XSS (for CodeQL lab work):
- Reflected XSS: search query is interpolated into HTML
- Stored XSS: guestbook comments are stored and rendered as HTML
"""

from urllib.parse import parse_qs, unquote

from robyn import Robyn, Request, Response, html

app = Robyn(__file__)


def query_value(request: Request, key: str) -> str:
    raw = request.query_params.get_first(key) or ""
    return unquote(raw)


def form_value(request: Request, key: str, default: str = "") -> str:
    if request.form_data and key in request.form_data:
        return request.form_data.get(key, default) or default
    body = request.body
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    values = parse_qs(body or "").get(key)
    return values[0] if values else default

# In-memory guestbook. Each item: {"author": str, "message": str}
COMMENTS = [
    {"author": "Ada", "message": "Hello from the first post."},
]


def page(title: str, body: str) -> Response:
    return html(
        f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>
    body {{ font-family: sans-serif; max-width: 720px; margin: 2rem auto; }}
    form {{ display: grid; gap: 0.5rem; margin: 1rem 0; }}
    input, textarea {{ padding: 0.4rem; }}
    .comment {{ border-bottom: 1px solid #ddd; padding: 0.75rem 0; }}
    nav a {{ margin-right: 1rem; }}
  </style>
</head>
<body>
  <nav>
    <a href="/">Guestbook</a>
    <a href="/search">Search</a>
  </nav>
  {body}
</body>
</html>"""
    )


@app.get("/")
def index(request: Request):
    items = "".join(
        f"""<article class="comment">
          <strong>{item['author']}</strong>
          <div>{item['message']}</div>
        </article>"""
        for item in reversed(COMMENTS)
    )
    body = f"""
    <h1>Guestbook</h1>
    <p>Leave a public message. HTML in the message is rendered as-is.</p>
    <form method="post" action="/comments">
      <label>Name <input name="author" required></label>
      <label>Message <textarea name="message" rows="4" required></textarea></label>
      <button type="submit">Post comment</button>
    </form>
    <h2>Comments</h2>
    {items or "<p>No comments yet.</p>"}
    """
    return page("Guestbook", body)


@app.post("/comments")
def add_comment(request: Request):
    author = form_value(request, "author", "anonymous")
    message = form_value(request, "message")
    COMMENTS.append({"author": author, "message": message})
    return Response(
        status_code=303,
        headers={"Location": "/"},
        description="",
    )


@app.get("/search")
def search(request: Request):
    query = query_value(request, "q")
    matches = []
    if query:
        lowered = query.lower()
        matches = [
            item
            for item in COMMENTS
            if lowered in item["author"].lower() or lowered in item["message"].lower()
        ]

    results = "".join(
        f"<li><strong>{item['author']}</strong>: {item['message']}</li>"
        for item in matches
    )
    # Reflected XSS: `query` is written into HTML without encoding.
    body = f"""
    <h1>Search</h1>
    <form method="get" action="/search">
      <input name="q" value="{query}" placeholder="Search comments">
      <button type="submit">Search</button>
    </form>
    <p>Results for: {query}</p>
    <ul>{results or "<li>No matches.</li>"}</ul>
    """
    return page("Search", body)


if __name__ == "__main__":
    app.start(host="127.0.0.1", port=8080)
