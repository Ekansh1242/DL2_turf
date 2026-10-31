# CampusSphere DL update

The trained CPU BiLSTM and synthetic dataset are in backend/ml.

From backend:
    python -m ml.generate_data
    python -m ml.train --epochs 20
    python -m ml.evaluate

Install requirements.txt, requirements-ml.txt, and CPU torch==2.6.0
from https://download.pytorch.org/whl/cpu first.

Evaluation outputs:
- backend/ml/artifacts/EVALUATION.md
- backend/ml/artifacts/evaluation.json
- CSV confusion matrices: actual labels in rows, predictions in columns

Includes intent precision/recall/F1, strict entity-span F1, field exact
accuracy, complete-request accuracy, rule-based comparison, and errors.
Checkpoint selection uses validation loss; test data is not used for fitting.

Copy .env.example to .env and set BOOKING_NLU_BACKEND=local.
Enter SMTP_HOST, SMTP_PORT=587, SMTP_USER, SMTP_PASS and SMTP_FROM.
Use your provider's SMTP/app password; never commit real credentials.
Restart the backend after changing settings.

Emails are sent after successful manual, AI, or sports-desk bookings.
PDF/SMTP failure does not undo a confirmed booking.
email_sent means SMTP acceptance, not guaranteed inbox delivery.
Sending is best effort, without persistent retries or exactly-once delivery.
No real email is sent by this build script.

Follow README.md for PostgreSQL migration/seed and frontend startup.
Local extraction needs no OpenAI key. Conflict selection falls back to rules
without one. Admin natural-language analytics still needs an OpenAI key.

Academic limitations:
All 3,010 examples are synthetic. Template families and exact texts are
disjoint across train/validation/test, but entity values recur.
The other intent is underrepresented (4/3/3 examples); macro F1 exposes this.
Collect human-written requests and balance classes before claiming
real-world accuracy. The model learns intent/entities, not scheduling.
This is a BiLSTM trained from scratch, not a fine-tuned transformer.
