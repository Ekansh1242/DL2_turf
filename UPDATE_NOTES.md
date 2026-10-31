# v2 verification

47 backend tests passed. Frontend TypeScript and production build passed.
Includes OTP login with expiry/attempt/rate limits, expiring JWTs with database-backed authorization, real evaluation UI, dataset downloads, local rule-based admin analytics, and balanced synthetic data.
New synthetic test: 600 examples; intent macro F1 0.8626, entity micro F1 0.9997, complete request accuracy 0.8700.
No live OTP email or concurrent PostgreSQL test was run here. Booking email transport retained. See V2_START_HERE.md.
