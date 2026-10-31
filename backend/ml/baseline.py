import re
from ml.model import values

def predict(text):
    patterns = {
        'sport': r'\b(?:table tennis|lawn tennis|football|cricket|basketball|badminton|pickleball|chess)\b',
        'date': r'\b(?:today|tomorrow|\d{4}-\d{2}-\d{2})\b',
        'time': r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b',
        'players': r'\b(\d+)\s+(?:players|people|students)\b'}
    spans = []
    for field, pattern in patterns.items():
        m = re.search(pattern, text, re.I)
        if m:
            start, end = m.span(1) if field == 'players' else m.span()
            spans.append({'label': field, 'start': start, 'end': end})
    lower = text.lower()
    intent = 'cancel' if any(w in lower for w in ['cancel','remove']) else 'availability' if any(w in lower for w in ['available','availability','free']) else 'book' if any(w in lower for w in ['book','reserve','play','arrange']) else 'other'
    return {'intent': intent, 'entities': spans, 'fields': values(text, spans)}
