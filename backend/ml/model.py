import re
import torch
from torch import nn

FIELDS = ['sport', 'date', 'time', 'players']
TAGS = ['O'] + [p + '-' + f for f in FIELDS for p in ['B', 'I']]
INTENTS = ['book', 'cancel', 'availability', 'other']

def tokenize(text):
    return [(m.group().lower(), m.start(), m.end()) for m in re.finditer(r'\d{4}-\d{2}-\d{2}|\d{1,2}:\d{2}|[a-zA-Z]+|\d+', text)]

class BookingModel(nn.Module):
    def __init__(self, vocab_size):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, 64, padding_idx=0)
        self.encoder = nn.LSTM(64, 64, batch_first=True, bidirectional=True)
        self.intent = nn.Linear(128, len(INTENTS))
        self.entities = nn.Linear(128, len(TAGS))
    def forward(self, ids):
        lengths = (ids != 0).sum(1).cpu()
        packed = nn.utils.rnn.pack_padded_sequence(self.embedding(ids), lengths, batch_first=True, enforce_sorted=False)
        encoded, (h, _) = self.encoder(packed)
        encoded, _ = nn.utils.rnn.pad_packed_sequence(encoded, batch_first=True, total_length=ids.shape[1])
        return self.intent(torch.cat([h[-2], h[-1]], dim=1)), self.entities(encoded)

def entities(text, tags):
    tokens = tokenize(text)
    spans, active = [], None
    for (_, start, end), tag in zip(tokens, tags):
        if tag == 'O':
            active = None
            continue
        prefix, field = tag.split('-', 1)
        if prefix == 'B' or active is None or active['label'] != field:
            active = {'label': field, 'start': start, 'end': end}
            spans.append(active)
        else:
            active['end'] = end
    return spans

def values(text, spans):
    result = {f: None for f in FIELDS}
    for span in spans:
        result[span['label']] = text[span['start']:span['end']].lower()
    return result

class Predictor:
    def __init__(self, path):
        torch.set_num_threads(2)
        checkpoint = torch.load(path, map_location='cpu', weights_only=True)
        self.vocab = checkpoint['vocab']
        self.model = BookingModel(len(self.vocab))
        self.model.load_state_dict(checkpoint['state_dict'])
        self.model.eval()
    def predict(self, text):
        tokens = tokenize(text)
        if not tokens or len(tokens) > 128:
            raise ValueError('Use a request containing 1–128 tokens.')
        ids = torch.tensor([[self.vocab.get(t[0], 1) for t in tokens]])
        with torch.no_grad():
            intent, tags = self.model(ids)
        spans = entities(text, [TAGS[i] for i in tags[0].argmax(-1).tolist()])
        return {'intent': INTENTS[int(intent.argmax(-1).item())], 'entities': spans, 'fields': values(text, spans)}
