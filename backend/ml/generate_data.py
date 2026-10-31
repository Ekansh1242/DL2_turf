"""Deterministic SYNTHETIC examples; templates are disjoint across splits."""
import json
import random
import re
from pathlib import Path

TEMPLATES = {
 'train': {
  'book': ['book {sport} {date} at {time} for {players} players', 'reserve a {sport} court at {time} {date} for {players} people', 'i want to play {sport} {date} at {time} with {players} players', 'please arrange {sport} {date} at {time} for {players} students'],
  'cancel': ['cancel my {sport} booking {date} at {time}', 'remove my reservation for {sport} at {time} {date}'],
  'availability': ['is {sport} available {date} at {time}', 'show free slots for {sport} {date} at {time}'],
  'other': ['hello there', 'thank you', 'what is the weather', 'where is the library']},
 'validation': {
  'book': ['could you reserve {sport} {date} at {time} for {players} players', 'get me a {sport} slot {date} at {time} for {players} students'],
  'cancel': ['please cancel the {sport} slot at {time} {date}'],
  'availability': ['can i check availability for {sport} at {time} {date}'],
  'other': ['good morning', 'help me with homework', 'tell me a joke']},
 'test': {
  'book': ['we need a {sport} booking {date} at {time} for {players} people', 'please book a slot for {sport} at {time} {date} with {players} players'],
  'cancel': ['i no longer need my {sport} reservation {date} at {time}'],
  'availability': ['are there any free {sport} courts {date} at {time}'],
  'other': ['hi campus assistant', 'when does the canteen close', 'thanks for helping']}}


# Synthetic negative examples: plausible non-booking campus questions.
TOPICS = ['library opening hours', 'canteen menu', 'exam timetable', 'lecture rooms',
          'hostel rules', 'bus routes', 'scholarships', 'attendance policy', 'tuition fees',
          'wifi access', 'lost identity cards', 'laboratory access', 'placement notices',
          'course registration', 'medical services', 'parking rules', 'club activities',
          'holiday notices', 'printing facilities', 'academic calendar', 'study rooms',
          'campus directions', 'assignment deadlines', 'mess timings', 'cultural events',
          'office contacts', 'admission documents', 'student discounts', 'internship forms',
          'library fines', 'water facilities', 'stationery shops', 'graduation requirements',
          'research clubs', 'student support', 'computer labs', 'transport passes',
          'canteen prices', 'scholarship forms', 'semester results']
CONTEXTS = ['for new students', 'for final year students', 'on the main campus',
            'for visitors', 'during the semester', 'during holidays', 'for my class',
            'for the upcoming term', 'for the student handbook', 'for freshers',
            'for hostel residents', 'for day scholars']
TEMPLATES['train']['other'] = ['tell me about {topic} {context}',
    'where can i find information on {topic} {context}', 'please explain {topic} {context}',
    'i need help understanding {topic} {context}']
TEMPLATES['validation']['other'] = ['could you explain the details of {topic} {context}',
    'who can help me with {topic} {context}']
TEMPLATES['test']['other'] = ['i am looking for guidance about {topic} {context}',
    'what should i know regarding {topic} {context}']
TEMPLATES['train']['book'] += ['please book {sport} at {time} {date} with {players} players',
    'can you reserve {sport} {date} at {time} for {players} people',
    'we need to play {sport} at {time} {date} with {players} students',
    'get a {sport} reservation {date} at {time} for {players} players']
TEMPLATES['train']['cancel'] += ['i want to cancel {sport} {date} at {time}',
    'please release my {sport} reservation {date} at {time}',
    'withdraw the {sport} booking at {time} {date}',
    'do not keep my {sport} booking {date} at {time}']
TEMPLATES['validation']['cancel'] += ['could you remove the {sport} reservation {date} at {time}']
TEMPLATES['test']['cancel'] += ['we cannot attend {sport} {date} at {time} so cancel the booking']
TEMPLATES['train']['availability'] += ['check whether {sport} is free {date} at {time}',
    'what is the availability of {sport} at {time} {date}',
    'can you show open slots for {sport} {date} at {time}',
    'are any {sport} slots available {date} at {time}']
TEMPLATES['validation']['availability'] += ['is there an open slot for {sport} {date} at {time}']
TEMPLATES['test']['availability'] += ['i only want to check if {sport} is free at {time} {date}']

def generate():
    rng = random.Random(42)
    seen = set()
    for split, templates in TEMPLATES.items():
        rows = []
        for intent, patterns in templates.items():
            target = {'train': 700, 'validation': 150, 'test': 150}[split]
            while sum(r['intent'] == intent for r in rows) < target:
                pattern = rng.choice(patterns)
                fields = {'sport': rng.choice(['football','cricket','basketball','badminton','pickleball','table tennis','lawn tennis','chess']), 'date': rng.choice(['today','tomorrow','day after tomorrow','2026-11-15','2026-12-20','2027-01-10','2027-02-14']), 'time': rng.choice(['8 am','9 am','10 am','11 am','12 pm','1 pm','2 pm','3 pm','4 pm','5 pm','6 pm']), 'players': str(rng.randint(1, 30)), 'topic': rng.choice(TOPICS), 'context': rng.choice(CONTEXTS)}
                # Include incomplete booking requests: missing entities stay absent.
                if intent == 'book' and rng.random() < .2:
                    pattern = re.sub(r' at \{time\}', '', pattern)
                if intent == 'book' and rng.random() < .2:
                    pattern = re.sub(r' \{date\}', '', pattern)
                text, spans, pos = '', [], 0
                for m in re.finditer(r'\{(\w+)\}', pattern):
                    text += pattern[pos:m.start()]
                    value = fields[m[1]]
                    if m[1] in ('sport', 'date', 'time', 'players'):
                        spans.append({'label': m[1], 'start': len(text), 'end': len(text)+len(value)})
                    text += value
                    pos = m.end()
                text += pattern[pos:]
                if rng.random() < .25:
                    text = text[0].upper() + text[1:]
                if rng.random() < .25:
                    text += rng.choice(['.', '!', '?'])
                if text in seen: continue
                seen.add(text)
                rows.append({'id': f'{split}-{len(rows):05}', 'source': 'synthetic-template-v2', 'text': text, 'intent': intent, 'entities': spans})
            
        rng.shuffle(rows)
        out = Path(__file__).parent/'data'/f'{split}.jsonl'
        out.parent.mkdir(exist_ok=True)
        out.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        print(split, len(rows))
if __name__ == '__main__': generate()
