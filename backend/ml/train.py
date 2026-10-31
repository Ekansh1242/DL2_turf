import argparse
import json
import random
from pathlib import Path
import torch
from ml.model import BookingModel, INTENTS, TAGS, tokenize

ROOT = Path(__file__).parent

def load(split):
    return [json.loads(s) for s in (ROOT/'data'/f'{split}.jsonl').read_text().splitlines()]

def gold_tags(row):
    tags = []
    for _, start, end in tokenize(row['text']):
        entity = next((e for e in row['entities'] if start >= e['start'] and end <= e['end']), None)
        tags.append('O' if entity is None else ('B-' if start == entity['start'] else 'I-') + entity['label'])
    return tags

def batch(rows, vocab):
    width = max(len(tokenize(r['text'])) for r in rows)
    ids = torch.zeros(len(rows), width, dtype=torch.long)
    tags = torch.full_like(ids, -100)
    for i, row in enumerate(rows):
        seq = [vocab.get(t[0], 1) for t in tokenize(row['text'])]
        ids[i,:len(seq)] = torch.tensor(seq)
        tags[i,:len(seq)] = torch.tensor([TAGS.index(t) for t in gold_tags(row)])
    return ids, torch.tensor([INTENTS.index(r['intent']) for r in rows]), tags

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--epochs',type=int,default=20)
    args = ap.parse_args()
    random.seed(42); torch.manual_seed(42); torch.set_num_threads(2)
    train, val = load('train'), load('validation')
    vocab = {'<pad>':0, '<unk>':1}
    for row in train:
        for t, _, _ in tokenize(row['text']):
            if t not in vocab: vocab[t] = len(vocab)
    model = BookingModel(len(vocab))
    opt = torch.optim.Adam(model.parameters(), lr=.003)
    loss_fn = torch.nn.CrossEntropyLoss()
    out = ROOT/'artifacts'; out.mkdir(exist_ok=True)
    best, history = float('inf'), []
    for epoch in range(args.epochs):
        random.shuffle(train); model.train(); total=0
        for start in range(0,len(train),64):
            x,y,t = batch(train[start:start+64],vocab)
            a,b = model(x)
            loss = loss_fn(a,y)+loss_fn(b.reshape(-1,len(TAGS)),t.reshape(-1))
            opt.zero_grad(); loss.backward(); opt.step(); total+=loss.item()
        model.eval()
        with torch.no_grad():
            x,y,t = batch(val,vocab); a,b=model(x)
            score=(loss_fn(a,y)+loss_fn(b.reshape(-1,len(TAGS)),t.reshape(-1))).item()
        history.append({'epoch':epoch+1,'train_batch_loss_sum':total,'validation_loss':score})
        if score < best:
            best=score
            torch.save({'state_dict':model.state_dict(),'vocab':vocab,'epoch':epoch+1},out/'booking_model.pt')
        print(history[-1],flush=True)
    (out/'training_history.json').write_text(json.dumps(history,indent=2))
if __name__ == '__main__': main()
