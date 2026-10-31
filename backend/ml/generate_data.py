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

def generate():
    rng = random.Random(42)
    seen = set()
    for split, templates in TEMPLATES.items():
        rows = []
        for intent, patterns in templates.items():
            target = {'train': 700, 'validation': 150, 'test': 150}[split] if intent != 'other' else len(patterns)
            while sum(r['intent'] == intent for r in rows) < target:
                pattern = rng.choice(patterns)
                fields = {'sport': rng.choice(['football','cricket','basketball','badminton','pickleball','table tennis','lawn tennis','chess']), 'date': rng.choice(['today','tomorrow','2026-11-15','2026-12-20']), 'time': rng.choice(['8 am','9 am','10 am','11 am','12 pm','1 pm','2 pm','3 pm','4 pm','5 pm','6 pm']), 'players': str(rng.randint(2, 22))}
                # Include incomplete booking requests: missing entities stay absent.
                if intent == 'book' and rng.random() < .15:
                    pattern = re.sub(r' at \{time\}', '', pattern)
                if intent == 'book' and rng.random() < .15:
                    pattern = re.sub(r' \{date\}', '', pattern)
                text, spans, pos = '', [], 0
                for m in re.finditer(r'\{(\w+)\}', pattern):
                    text += pattern[pos:m.start()]
                    value = fields[m[1]]
                    spans.append({'label': m[1], 'start': len(text), 'end': len(text)+len(value)})
                    text += value
                    pos = m.end()
                text += pattern[pos:]
                if text in seen: continue
                seen.add(text)
                rows.append({'id': f'{split}-{len(rows):05}', 'source': 'synthetic-template', 'text': text, 'intent': intent, 'entities': spans})
            
        rng.shuffle(rows)
        out = Path(__file__).parent/'data'/f'{split}.jsonl'
        out.parent.mkdir(exist_ok=True)
        out.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        print(split, len(rows))
if __name__ == '__main__': generate()
