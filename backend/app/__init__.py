from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .api.routes import router as api_router


app = FastAPI(title="OpenConvert API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home():
    return """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>OpenConvert API</title>
  </head>
  <body style="font-family:system-ui;margin:40px">
    <h1>OpenConvert API</h1>
    <p>The backend server is running.</p>
    <ul>
      <li><a href="/docs">API documentation</a></li>
      <li><a href="/health">Health check</a></li>
      <li><a href="/api/v1/capabilities">Capabilities</a></li>
    </ul>
  </body>
</html>
"""


@app.get("/health")
def health():
    return {"status": "ok"}