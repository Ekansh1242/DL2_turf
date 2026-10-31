import { useEffect, useState } from 'react';
import { modelEvaluation, downloadModelDataset, ModelEvaluation, ModelScores } from '../api/client';
const pct = (v: number) => `${(v * 100).toFixed(2)}%`;
function Confusion({ name, score }: { name: string; score: ModelScores }) {
  const max = Math.max(1, ...score.confusion_matrix.flat());
  return <section className="glass-card rounded-xl p-4 overflow-x-auto">
    <h3 className="font-semibold mb-2">{name}: intent confusion matrix</h3>
    <p className="text-xs text-gray-500 mb-3">Rows: actual intent. Columns: predicted intent. Counts, not percentages.</p>
    <table className="w-full text-xs text-center"><thead><tr><th className="p-2">Actual / Predicted</th>{score.confusion_matrix_labels.map(l=><th className="p-2" key={l}>{l}</th>)}</tr></thead>
      <tbody>{score.confusion_matrix.map((row,i)=><tr key={i}><th className="p-2 text-left">{score.confusion_matrix_labels[i]}</th>{row.map((v,j)=><td key={j} className="p-3 border border-white" style={{background:`rgba(124,58,237,${0.06 + .6 * v / max})`}}>{v}</td>)}</tr>)}</tbody>
    </table>
  </section>;
}
export default function ModelEvaluationTab({ token }: {token: string}) {
  const [report,setReport]=useState<ModelEvaluation|null>(null);
  const [error,setError]=useState('');
  useEffect(()=>{ modelEvaluation(token).then(setReport).catch(e=>setError(e.message)); },[token]);
  if (!report) return <p role="status">{error || 'Loading measured evaluation…'}</p>;
  function downloadReport() {
    const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));
    const a=document.createElement('a');a.href=url;a.download='campussphere-evaluation.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  return <div className="flex flex-col gap-5">
    <div className="glass-card rounded-xl p-4">
      <h2 className="text-lg font-semibold">Deep learning evaluation</h2>
      <p className="text-sm mt-2">Joint BiLSTM intent classification and BIO entity extraction, trained from scratch. Compared with a rule-based baseline on the same held-out test set.</p>
      <p className="text-sm text-amber-800 bg-amber-50 rounded-lg p-3 mt-3">Synthetic data only. Templates are separated across splits, but entity values recur. These scores do not establish accuracy on real student requests.</p>
      <p className="text-xs text-gray-500 mt-2">Measured offline after training; checkpoint selected using validation loss only.</p>
    </div>
    <section className="glass-card rounded-xl p-4 overflow-x-auto"><h3 className="font-semibold mb-3">Model comparison — {report.bilstm.n} test requests</h3>
      <table className="w-full text-sm text-left"><thead><tr>{['Model','Intent macro F1','Entity micro F1','Complete request'].map(t=><th className="p-2" key={t}>{t}</th>)}</tr></thead>
        <tbody>{(['bilstm','rules'] as const).map(key=><tr className="border-t" key={key}><td className="p-2">{key === 'bilstm' ? 'BiLSTM' : 'Rules baseline'}</td><td className="p-2">{pct(report[key].intent_report['macro avg']['f1-score'])}</td><td className="p-2">{pct(report[key].entity_micro.f1)}</td><td className="p-2">{pct(report[key].complete_request_accuracy)}</td></tr>)}</tbody>
      </table><p className="text-xs text-gray-500 mt-3">Complete request: correct intent and all exact entity spans. Entity micro F1 uses exact span and type matching.</p>
    </section>
    <section className="glass-card rounded-xl p-4 overflow-x-auto"><h3 className="font-semibold mb-3">Dataset distribution</h3>
      <table className="w-full text-sm text-left"><thead><tr><th className="p-2">Split</th>{['book','cancel','availability','other'].map(t=><th className="p-2" key={t}>{t}</th>)}</tr></thead>
        <tbody>{Object.entries(report.dataset_counts).map(([split,counts])=><tr key={split} className="border-t"><td className="p-2">{split}</td>{['book','cancel','availability','other'].map(t=><td className="p-2" key={t}>{counts[t] || 0}</td>)}</tr>)}</tbody></table>
    </section>
    <Confusion name="BiLSTM" score={report.bilstm}/><Confusion name="Rules baseline" score={report.rules}/>
    {(['bilstm','rules'] as const).map(key=><section key={key} className="glass-card rounded-xl p-4 overflow-x-auto">
      <h3 className="font-semibold mb-3">{key}: intent precision, recall and F1</h3><table className="w-full text-xs text-left"><thead><tr>{['Intent','Precision','Recall','F1','Support'].map(t=><th className="p-2" key={t}>{t}</th>)}</tr></thead><tbody>{report[key].confusion_matrix_labels.map(label=>{const r=report[key].intent_report[label];return <tr key={label} className="border-t"><td className="p-2">{label}</td><td className="p-2">{pct(r.precision)}</td><td className="p-2">{pct(r.recall)}</td><td className="p-2">{pct(r['f1-score'])}</td><td className="p-2">{r.support}</td></tr>;})}</tbody></table>
      <h3 className="font-semibold mt-5 mb-3">Entity extraction</h3><table className="w-full text-xs text-left"><thead><tr>{['Field','Precision','Recall','Span F1','Value accuracy'].map(t=><th className="p-2" key={t}>{t}</th>)}</tr></thead><tbody>{Object.entries(report[key].entity_per_field).map(([field,r])=><tr key={field} className="border-t"><td className="p-2">{field}</td><td className="p-2">{pct(r.precision)}</td><td className="p-2">{pct(r.recall)}</td><td className="p-2">{pct(r.f1)}</td><td className="p-2">{pct(report[key].field_exact_accuracy[field])}</td></tr>)}</tbody></table>
      <p className="text-xs text-gray-500 mt-2">Value accuracy includes correctly absent fields. Read it together with entity recall.</p>
    </section>)}
    <div className="flex flex-wrap gap-2"><button onClick={downloadReport} className="gradient-btn text-white rounded-lg px-3 py-2 text-sm">Download full report</button>{['train','validation','test'].map(split=><button className="glass-card rounded-lg px-3 py-2 text-sm" key={split} onClick={()=>downloadModelDataset(split,token).catch(e=>setError(e.message))}>Download {split} data</button>)}</div>
    {error && <p role="alert" className="text-red-600">{error}</p>}
    <details className="glass-card rounded-xl p-4 text-xs"><summary>Reproducibility and error examples</summary><p className="break-all mt-2">Checkpoint SHA-256: {report.metadata.checkpoint_sha256}</p><p className="break-all mt-2">Test data SHA-256: {report.metadata.test_sha256}</p><pre className="overflow-x-auto mt-3">{JSON.stringify(report.bilstm.errors.slice(0,10),null,2)}</pre></details>
  </div>;
}
