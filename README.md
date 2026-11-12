# NoticeTrust

Responsive React frontend for comparing notice screenshots with reference documents. Built for the AI4Elections hackathon with an ivory, forest-green and editorial-serif design.

## Run

Node 24 recommended.

```sh
npm ci
npm run dev
```

Open the Vite address printed in the terminal. `npm run build` produces a static site in `dist/`; `npm run preview` serves that build. Fonts are bundled locally; no Google Fonts request is made.

## What works

- Mobile navigation, accessible native dialogs and keyboard focus indicators.
- JPG/PNG selection, drag-and-drop, preview, replacement and removal; 10 MB / 25 megapixel limits and image decoding validation.
- Three explicitly simulated examples: differences, matching visible content, and unable to verify.
- Source collection search, source metadata, comparison layout and mobile document tabs.
- About/limitations page, upload and service errors, cancellable processing.

## Real verification integration

Without `VITE_API_BASE_URL`, images stay in the browser and cannot produce a real verification claim. Uploaded images return an explicit service-unavailable result. Examples are fictional and labelled throughout. There is no reviewer authentication, database, OCR service or institutional endorsement in this frontend.

Set `VITE_API_BASE_URL` in a local `.env` file (see `.env.example`) and rebuild. Never put secrets in Vite environment variables. The API must implement CORS for the frontend origin and enforce its own validation, access control, retention and rate limits.

`POST /api/verifications` accepts multipart field `file` and returns `{ "id": "…", "access_token": "…" }`. Polling `GET /api/verifications/{id}` sends `Authorization: Bearer <access_token>` and expects `status` of `processing`, `completed` or `failed`. Optional `stage`: `reading`, `finding`, `comparing`.

Example completed payload:

```json
{
  "status": "completed",
  "outcome": "differences",
  "comparison_scope": "Readable text on page 1",
  "source": {"title": "Source title", "publisher": "Publisher", "publication_date": "2026-11-01", "url": "https://example.org/notice"},
  "differences": [{"field": "Date", "uploaded": "12 April", "published": "26 April"}]
}
```

Allowed outcomes: `match`, `differences`, `unverified`. Optional `reason` explains inability to verify. Source URLs permit HTTP(S) only. Job tokens are held in memory. Polling cancellation stops frontend requests; server job cancellation requires backend support.

## Validation

```sh
npm test
npm run build
npx playwright test
```

Browser tests use `/usr/bin/chromium` by default; override with `CHROMIUM_PATH`, or install a Playwright browser and update the config. CI runs unit checks and production build. Test images are generated locally and contain no personal data.

## Shipping

The static build can be hosted on GitHub Pages, Netlify or Vercel. Relative asset paths support repository subdirectories. GitHub code publication is separate from enabling web hosting. No hosting service is enabled automatically.

## Next frontend work

Connect real source-list endpoints, add reviewer auth/queue after the backend contract is ready, replace fictional references with authorised records, and add native-speaker-reviewed Pidgin explanations. Avoid generated electoral guidance.

## Design and licence

Original NoticeTrust implementation informed by the team's approved visual mockup. No Cosmos UI source was copied. Code: MIT. Bundled font packages carry their own open font licences.
