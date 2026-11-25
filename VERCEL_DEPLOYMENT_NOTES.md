# ShelfSignal Vercel deployment notes

1. Import the GitHub repository into Vercel. Root directory: `./`.
2. Framework preset: Flask (auto-detected). Leave build and output overrides blank.
3. Do not add a catch-all `vercel.json` rewrite. Flask is automatically routed by Vercel.
4. Add `DATABASE_URL` using a real managed MySQL connection URL.
5. Add `SECRET_KEY` with a long random value.
6. Add `FLASK_DEBUG=0`.
7. Set `SHELFSIGNAL_SEED_DEMO=1` on the first deployment if you want the included synthetic sample data; otherwise set `0` and upload your own CSV.
8. Redeploy after changing environment variables.

The page and `/api/health` can load without MySQL. Database-backed API requests return a clear HTTP 503 if `DATABASE_URL` is missing or invalid, rather than failing while Vercel imports the Flask app.

Static assets are served from `public/static/` by Vercel. Locally, Flask serves that same folder at `/static/`.

Runtime files and model cache use `/tmp/shelfsignal`, not the read-only deployment bundle. `/tmp` is temporary and must not be used for persistent business data.
