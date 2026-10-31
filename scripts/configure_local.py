"""Set up local auth settings without changing SMTP credentials or the database."""
from pathlib import Path
import re
import secrets


def configure(root):
    path = root / '.env'
    text = path.read_text(encoding='utf-8-sig') if path.exists() else (root / '.env.example').read_text()

    def value(key):
        match = re.search(r'(?m)^' + re.escape(key) + r'=(.*)$', text)
        return match.group(1).strip().strip('\'"') if match else ''

    def put(key, content):
        nonlocal text
        text = re.sub(r'(?m)^' + re.escape(key) + r'=.*\r?\n?', '', text)
        text = text.rstrip() + '\n' + key + '=' + content + '\n'

    key = value('JWT_SECRET')
    if len(key) < 32 or key == 'dev-secret-change-me':
        put('JWT_SECRET', secrets.token_urlsafe(48))
    if not value('ADMIN_EMAILS'):
        sender = value('SMTP_USER')
        if sender and '@' in sender and not sender.startswith(('your-', 'YOUR_')):
            put('ADMIN_EMAILS', sender)
    if not value('ALLOWED_EMAIL_DOMAINS'):
        put('ALLOWED_EMAIL_DOMAINS', 'rknec.edu')
    if not value('CORS_ORIGINS'):
        put('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173')
    put('BOOKING_NLU_BACKEND', 'local')
    put('ANALYTICS_BACKEND', 'local')
    path.write_text(text, encoding='utf-8')
    print('Local authentication settings saved. SMTP settings and database records were not changed.')
    print('ADMIN_EMAILS must contain a real inbox you control. Restart the backend and sign in using its email code.')
    print('Revoke previously exposed credentials in your email provider account; this script cannot revoke them.')


if __name__ == '__main__':
    configure(Path(__file__).resolve().parents[1])
