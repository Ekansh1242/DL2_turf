# CampusSphere: Deep Learning Turf Booking

Campus sports bookings with a trained BiLSTM for intent classification and entity extraction, deterministic availability checks, email OTP login, booking receipt emails, and an admin model-evaluation dashboard.

Read **V2_START_HERE.md** for current setup and limitations. Older instructions in DL_START_HERE.md and DL_GUIDE.md are historical.

## Updating your existing local project

Stop the backend and frontend, pull this branch, and run from the project root:

```powershell
py -3.12 scripts/configure_local.py
```

This preserves the working SMTP settings in your ignored `.env`, replaces a missing/default JWT key with a random signing key, and configures local booking inference and local rule-based analytics. Keep PostgreSQL running. Restart the backend using your existing training virtual environment, and restart Vite from frontend. New OTP tables are created on backend startup; booking records are retained.

Sign in using a real allowed college inbox or an address in `ADMIN_EMAILS`. Ownership is verified by email OTP. No demo admin password exists, and the old email-only login is removed. `ADMIN_EMAILS` is server configuration, never a user-selectable role. Revoke any credentials previously shared in screenshots through the provider's account settings.

## Deep learning component

- Learned embeddings, bidirectional LSTM, intent classification head and BIO entity extraction head.
- Four intents: book, cancel, availability, other.
- Entities: sport, date, time, player count.
- Balanced **synthetic** data: 2,800 training, 600 validation and 600 test examples.
- Vocabulary fitted on training data; checkpoint selected using validation loss.
- The report includes precision/recall/F1, strict entity-span F1, field accuracy, full-request accuracy, both confusion matrices, and comparison with a rule-based baseline.
- Open the admin **Model Evaluation** tab to view measured results and download the report/datasets.

The data is generated from disjoint sentence templates, with recurring entity values. Metrics do not establish performance on real student language. Admin **Ask Analytics** uses transparent keyword routing over read-only queries by default; it is separate from the DL booking model and requires no external API key.

## Validation

From backend, using Python 3.12 with requirements.txt, requirements-ml.txt and CPU PyTorch 2.6.0 installed:

```bash
pytest tests -q
python -m ml.generate_data
python -m ml.train --epochs 25
python -m ml.evaluate
```

From frontend: `npm ci` and `npm run build`.

47 backend tests and the frontend production build pass. SMTP is mocked in tests; verify a real OTP on your machine. PostgreSQL concurrency and production deployment were not validated in this cloud task. Configure HTTPS, private database access, trusted proxy settings and exact CORS origins before public hosting.
