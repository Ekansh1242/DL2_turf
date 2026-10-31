# CampusSphere v2: OTP, evaluation UI, balanced data

## Sign in

After pulling this branch, stop the backend and frontend and run `py -3.12 scripts/configure_local.py` from the project root. Keep your existing .env; do not replace it with .env.example. The configuration helper preserves your working SMTP settings, uses the existing sender inbox as ADMIN_EMAILS if no admin list exists, and replaces an absent/default JWT signing key with a random 48-byte token. The signing key is stored only in local .env, never in the downloadable ZIP. Existing sessions signed with the old key become invalid.

Students use allowed college email domains (default rknec.edu). Staff use real inboxes in ADMIN_EMAILS, a comma-separated server-side setting. The sender Gmail and the admin inbox can be the same address. The user must receive and verify a code before obtaining ANY session. The old email-only /auth/login endpoint is removed. You cannot impersonate the old sample staff mailbox anymore. Configure an inbox you control; never expose the SMTP password or JWT secret.

A sign-in code expires after five minutes, permits five incorrect attempts, is invalidated on resend, and is consumed on successful verification. Resend cooldown: 60 seconds. Email requests: 10 per address per hour and 20 per client IP per hour. Verification requests: 60 per client IP per hour. Only an HMAC digest is stored. Rate limits and challenges persist in database tables. Tokens expire after one hour; admin authorization rechecks the database role. Changing ADMIN_EMAILS grants a listed user admin on their next verified login; removing an address does not automatically demote an existing database admin. Demote the user explicitly if removing access.

OTP delivery uses the same SMTP transport that you confirmed works for booking emails. Unit tests mock SMTP; this cloud environment did not send live OTPs. Confirm one real sign-in code on your computer before presenting. No OTP, password or signing key is returned in API responses or logged by the application.

## Start locally

From the generated project's parent, reuse training-venv/Scripts/python.exe (Windows).
From project root: docker compose up postgres redis -d.
From backend: <venv-python> -m uvicorn app.main:app --reload --port 8000.
From frontend in another terminal: npm ci, then npm run dev.
New OTP tables are additive and created on backend startup; existing booking records are retained.
Restart the backend after editing .env. Do not put secrets in VITE_ variables.

## Evaluation tab

After OTP login with a configured admin inbox, open Model Evaluation.
It shows BiLSTM versus rules, BOTH confusion matrices, all four intent classes' precision/recall/F1 and support, entity precision/recall/F1 and per-field accuracy, dataset distribution, examples of mistakes, and hashes. Download buttons provide the full JSON report and all three JSONL splits. Results are read from artifacts produced by actual evaluation, not hardcoded dashboard scores.

## Dataset v2

4,000 custom SYNTHETIC labeled examples: 2,800 train (700 per intent), 600 validation and 600 test (150 per intent per split). No real student records were invented or claimed. Varied campus questions balance the other class. Additional request templates, punctuation, casing, missing fields, group sizes and dates are included. Template families and exact texts are separated across splits; entity values recur, and paraphrases can remain similar. This improves the sample exercise but does not establish human-language generalization.

Training: python -m ml.generate_data; python -m ml.train --epochs 25; python -m ml.evaluate (from backend).
Vocabulary fits training only. The best validation-loss checkpoint is saved. The held-out test set is evaluated only after training. Report actual values from EVALUATION.md; do not reuse the old 99.34% claim.

## Admin analytics

Ask Analytics defaults to local keyword routing over fixed read-only database queries. It requires NO OpenAI key and handles sports, peak hours, equipment damage/loss, departments, years, trends, students, fines and totals. Unsupported questions get a clear explanation. It is rule-based analytics, NOT the trained BiLSTM and NOT generative AI. The original optional LLM mode is available with ANALYTICS_BACKEND=llm and a valid OpenAI API key/billing. The student conflict path still has its original explicitly marked rule fallback when an optional LLM is unavailable.

## Deployment limits

Local tested: 64 backend tests and frontend TypeScript/production build. The tests use SQLite and mocked SMTP; PostgreSQL concurrent row locking and live OTP delivery were not validated here. Use one database-backed deployment and HTTPS, configure exact CORS_ORIGINS for the deployed frontend, keep PostgreSQL/Redis private, configure trusted reverse-proxy handling of client IPs, back up the DB, and revoke previously exposed Google app passwords before hosting. The updater cannot revoke credentials at Google. Email is still synchronous/best-effort, without persistent delivery retries. Expired throttle rows can be pruned periodically. Local OTP security improvements alone do not certify production readiness.

## Booking date normalization

The local parser explicitly normalizes ordinal/month dates such as 1st NOV, November 1st and ISO dates, in addition to today/tomorrow/day after tomorrow. Missing years use the current reference year without guessing a future rollover. Invalid or conflicting dates request clarification. This deterministic parsing layer supplements the trained model; it is not additional model training and does not change the offline raw-model metrics.
