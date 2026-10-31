"""Evaluate the frozen checkpoint on test only; no fitting or threshold tuning."""
import csv
import hashlib
import json
from sklearn.metrics import classification_report, confusion_matrix
from ml import baseline
from ml.model import Predictor, INTENTS, FIELDS, values
from ml.train import ROOT, load

def measure(rows, predictions):
    true = [r['intent'] for r in rows]; pred=[r['intent'] for r in predictions]
    counts={f:[0,0,0] for f in FIELDS}
    correct={f:0 for f in FIELDS}; exact=0
    errors=[]
    for row,p in zip(rows,predictions):
        gold={(e['label'],e['start'],e['end']) for e in row['entities']}
        guessed={(e['label'],e['start'],e['end']) for e in p['entities']}
        for f in FIELDS:
            g={e for e in gold if e[0]==f}; q={e for e in guessed if e[0]==f}
            counts[f][0]+=len(g&q); counts[f][1]+=len(q-g); counts[f][2]+=len(g-q)
            correct[f]+=values(row['text'],row['entities'])[f]==p['fields'][f]
        ok=row['intent']==p['intent'] and gold==guessed
        exact+=ok
        if not ok: errors.append({'text':row['text'],'gold_intent':row['intent'],'gold_entities':row['entities'],'prediction':p})
    def scores(c):
        tp,fp,fn=c
        precision=tp/(tp+fp) if tp+fp else 0
        recall=tp/(tp+fn) if tp+fn else 0
        return {'precision':precision,'recall':recall,'f1':2*precision*recall/(precision+recall) if precision+recall else 0,'tp':tp,'fp':fp,'fn':fn}
    return {'n':len(rows),'intent_report':classification_report(true,pred,labels=INTENTS,output_dict=True,zero_division=0),'confusion_matrix_labels':INTENTS,'confusion_matrix':confusion_matrix(true,pred,labels=INTENTS).tolist(),'entity_per_field':{f:scores(c) for f,c in counts.items()},'entity_micro':scores([sum(c[i] for c in counts.values()) for i in range(3)]),'field_exact_accuracy':{f:v/len(rows) for f,v in correct.items()},'complete_request_accuracy':exact/len(rows),'errors':errors}

def main():
    rows=load('test'); predictor=Predictor(ROOT/'artifacts/booking_model.pt')
    reports={name:measure(rows,[fn(r['text']) for r in rows]) for name,fn in [('bilstm',predictor.predict),('rules',baseline.predict)]}
    reports['metadata']={'dataset':'Balanced synthetic dataset v2; disjoint template families; recurring entity values; not evidence of real-user generalization','test_sha256':hashlib.sha256((ROOT/'data/test.jsonl').read_bytes()).hexdigest(),'checkpoint_sha256':hashlib.sha256((ROOT/'artifacts/booking_model.pt').read_bytes()).hexdigest()}
    out=ROOT/'artifacts'
    (out/'evaluation.json').write_text(json.dumps(reports,indent=2))
    lines=['# Held-out synthetic test evaluation','',reports['metadata']['dataset'],'','| Model | Intent macro F1 | Entity micro F1 | Complete request accuracy |','|---|---:|---:|---:|']
    for name in ['bilstm','rules']:
        r=reports[name]; lines.append(f"| {name} | {r['intent_report']['macro avg']['f1-score']:.4f} | {r['entity_micro']['f1']:.4f} | {r['complete_request_accuracy']:.4f} |")
        with (out/f'{name}_confusion_matrix.csv').open('w') as f:
            writer=csv.writer(f, lineterminator='\n');writer.writerow(['actual / predicted']+INTENTS)
            writer.writerows([[label]+values for label,values in zip(INTENTS,r['confusion_matrix'])])
    lines += ['', 'Full precision/recall/F1, field accuracies, strict span matches, and every error: evaluation.json.', 'Confusion matrices: *_confusion_matrix.csv. Rows are actual labels, columns predicted.', 'Field accuracy includes absent fields. Complete request accuracy requires correct intent and every exact entity span.', 'Checkpoint chosen by validation loss only. Test data is used only after training.']
    (out/'EVALUATION.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))
if __name__=='__main__': main()
