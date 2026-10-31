> Superseded by V2_START_HERE.md. Dataset counts, login and analytics changed in v2.

# CampusSphere DL edition

## What is included

- A genuine trainable PyTorch BiLSTM: 64-dimensional learned embeddings, a bidirectional LSTM with 64 hidden units in each direction, a four-class intent head, and a BIO token-tagging head.
- Intents: book, cancel, availability, other. Entities: sport, date, time, players.
- 3,010 labeled synthetic requests: 2,104 train, 453 validation, 453 test, with character-offset entity annotations in JSONL. Generator seed: 42. Sentence template families are disjoint across splits and exact duplicate texts are excluded globally. Vocabulary is fit only on training data.
- A trained CPU checkpoint in backend/ml/artifacts/booking_model.pt. Model selection uses validation loss, not test results. Twenty epochs were actually run; the saved checkpoint is the epoch with lowest validation loss.
- Intent precision/recall/F1 and confusion matrices; strict entity span precision/recall/F1; per-field exact accuracy; full-request accuracy; rule-based baseline comparison; error examples and file hashes. See backend/ml/artifacts/EVALUATION.md and evaluation.json.
- Local model extraction wired into the existing booking graph. Booking restrictions and availability remain deterministic. Non-booking intents are recognized and redirected to the appropriate existing UI; the model does not cancel bookings automatically.
- Confirmation email with PDF receipt for successful manual, AI, and sports-desk bookings. Proposals and rejected bookings do not send confirmations. Notification/PDF failure does not undo a confirmed booking. Both booking APIs expose email_sent; this means SMTP accepted the message, not guaranteed inbox delivery.

## Install (Python 3.12)

From the extracted campussphere directory:

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt -r backend/requirements-ml.txt
pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
cp .env.example .env
```

Edit .env locally. Set BOOKING_NLU_BACKEND=local to use the trained model. Without this setting the original LLM extraction remains the default for backward compatibility. The supplied Docker Compose file selects local by default and passes SMTP settings to the backend. Docker builds install CPU PyTorch too.

Keep the working directory at the project root when running:

```bash
docker compose up postgres redis -d
cd backend
uvicorn app.main:app --reload --port 8000
```

The backend loads .env from the project directory via python-dotenv. Follow the original README for the PostgreSQL migration and seeding; the DB exclusion constraint requires PostgreSQL and is not tested by SQLite tests. In another terminal, from frontend run npm ci and npm run dev.

Local intent/entity extraction needs no API key. Conflict candidate selection uses the original LLM if configured, otherwise its explicit deterministic fallback; admin natural-language analytics still requires an OpenAI API key. Missing model files fail rather than silently substituting fake predictions.

## Reproduce training and evaluation

From backend, with the virtual environment active:

```bash
python -m ml.generate_data
python -m ml.train --epochs 20
python -m ml.evaluate
pytest tests -q
```

Training uses Adam (learning rate 0.003), batch size 64, seed 42, and the sum of intent and BIO-tag cross entropy. Padding is excluded from token loss. Validation loss selects the checkpoint. Training history and the actual training log are included. Running these commands overwrites generated data and artifacts. Do not edit the test set to improve reported scores.

The evaluation is a separate reproducible command, not a live score displayed on booking requests. Confusion matrix CSVs use actual labels as rows and predicted labels as columns. Entity scores require exact label and character-span matches. Full-request accuracy requires correct intent plus every span. Field accuracy includes null fields, so read it alongside entity recall. evaluation.json contains all four intent classes even when a class has no correct predictions.

## Email configuration

Set these in your local .env; do not commit the real values:

```dotenv
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-sender@gmail.com
SMTP_PASS=your-provider-app-password
SMTP_FROM=your-sender@gmail.com
```

Use your provider's SMTP credentials (Gmail requires an app password where supported). STARTTLS uses certificate verification. The sender must be permitted by the provider. Restart the backend after changing settings. Book a slot inside its allowed window with a real recipient address and check email_sent and backend logs. If SMTP is unconfigured, booking still works and email_sent is false.

Transport and PDF attachment handling are tested with mocked SMTP; no real emails were sent during development. Sending is synchronous and best effort, with a 10-second SMTP timeout; there is no durable retry queue or exactly-once delivery guarantee. Use an outbox worker before production deployment if guaranteed retries are required.

## Academic limitations — disclose these

This is a small supervised model trained from scratch, not a fine-tuned pretrained transformer. All data is generated, not collected from real students. Entity values recur across splits; only exact texts and template families are separated. Most examples belong to three in-domain intents; the other class has just 4/3/3 examples in train/validation/test. Its scores are unstable, which is visible in macro F1. High full-request accuracy on these templates does not establish robustness to real language.

The included baseline can outperform the neural model on extraction because the sample language is regular. Report that honestly. Before final submission collect consented human-written requests, expand and balance the other class, add typos and paraphrases, and evaluate once on a separately held-out human set. Missing details are represented, but ambiguity, multiple requests, Hindi, arbitrary dates, fractional times, and multi-turn context are not comprehensively covered. Non-whole-hour times request clarification rather than being rounded into a booking.

The DL contribution is intent classification and entity extraction. Rule-based scheduling, API-based conflict reasoning, and email delivery are separate components. Do not claim the trained model learned scheduling or that synthetic metrics represent production accuracy.
