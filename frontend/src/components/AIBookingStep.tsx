import { useState } from "react";
import { motion } from "framer-motion";
import {
  Sparkles, Loader2, CheckCircle2, AlertCircle, Brain, ListChecks, Zap, Clock, HelpCircle, Check, ShieldAlert,
} from "lucide-react";
import { aiBook, confirmBooking, AIBookResult, TraceStep } from "../api/client";

const NODE: Record<string, { label: string; icon: JSX.Element }> = {
  booking_node: { label: "Booking Agent", icon: <Brain size={14} /> },
  scheduling_conflict_node: { label: "Scheduling & Conflict Agent", icon: <ListChecks size={14} /> },
  commit_node: { label: "Commit (deterministic)", icon: <Zap size={14} /> },
};

const EXAMPLES = ["Football at 6pm today", "Book badminton this evening", "Cricket tomorrow morning"];

function fmt(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function TraceRow({ step }: { step: TraceStep }) {
  const n = NODE[step.node] ?? { label: step.node, icon: <Zap size={14} /> };
  const badge =
    step.status === "completed" ? "text-emerald-600 bg-emerald-50"
    : step.status === "fallback" ? "text-amber-600 bg-amber-50"
    : "text-red-600 bg-red-50";
  return (
    <div className="glass-card rounded-xl p-3 flex items-start gap-3">
      <div className="w-7 h-7 rounded-lg gradient-btn text-white flex items-center justify-center shrink-0">{n.icon}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-semibold text-violet-700">{n.label}</span>
          <span className="flex items-center gap-2">
            <span className={`badge ${badge}`}>{step.status}</span>
            <span className="text-[10px] text-gray-400">{step.duration_ms} ms</span>
          </span>
        </div>
        <div className="text-xs text-gray-600 mt-0.5">{step.summary}</div>
      </div>
    </div>
  );
}

export default function AIBookingStep({ token }: { token: string }) {
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AIBookResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [confirmedId, setConfirmedId] = useState<string | null>(null);
  const [confirmError, setConfirmError] = useState<string | null>(null);

  async function run(text: string) {
    if (!text.trim()) return;
    setMessage(text); setError(null); setResult(null); setConfirmedId(null); setConfirmError(null); setLoading(true);
    try { setResult(await aiBook(text, token)); }
    catch (e) { setError(e instanceof Error ? e.message : "AI booking failed"); }
    finally { setLoading(false); }
  }

  async function confirm() {
    if (!result?.proposal) return;
    setConfirming(true); setConfirmError(null);
    try {
      const r = await confirmBooking(result.proposal.resource_id, result.proposal.slot_start, result.proposal.slot_end, token);
      if (r.success && r.booking_id) setConfirmedId(r.booking_id);
      else setConfirmError(r.message);
    } catch (e) { setConfirmError(e instanceof Error ? e.message : "Could not confirm"); }
    finally { setConfirming(false); }
  }

  const s = result?.status;
  const tone = s === "confirmed" ? "emerald" : s === "needs_confirmation" || s === "recommendation" ? "violet" : s === "needs_info" ? "blue" : "amber";
  const toneCls: Record<string, string> = {
    emerald: "bg-emerald-50 border-emerald-200 text-emerald-700", violet: "bg-violet-50 border-violet-200 text-violet-800",
    blue: "bg-blue-50 border-blue-200 text-blue-700", amber: "bg-amber-50 border-amber-200 text-amber-700",
  };
  const heading: Record<string, string> = {
    confirmed: "Booking confirmed", needs_confirmation: "Preferred slot is taken — confirm an alternative",
    recommendation: "Preferred slot is taken — best option isn't open for booking yet", needs_info: "I need a bit more detail",
    rejected: "I can't book that", not_yet_open: "Booking window not open yet", escalated: "No suitable slot found",
  };

  return (
    <div className="px-4 py-6 max-w-lg mx-auto">
      <div className="flex items-center gap-2 justify-center mb-1">
        <Sparkles size={18} className="text-violet-600" />
        <h2 className="text-lg font-bold gradient-text">AI Booking</h2>
      </div>
      <p className="text-xs text-gray-500 text-center mb-5">Describe what you want. The agent checks real availability and shows every step it takes.</p>

      <form onSubmit={(e) => { e.preventDefault(); run(message); }} className="glass-card rounded-2xl p-4 mb-3">
        <textarea className="input-field" rows={2} placeholder="e.g. Football at 6pm today for 10 players"
          value={message} onChange={(e) => setMessage(e.target.value)} />
        <button type="submit" disabled={loading || !message.trim()}
          className="gradient-btn text-white rounded-xl py-2.5 text-sm font-medium w-full mt-3 flex items-center justify-center gap-2">
          {loading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
          {loading ? "Agent working..." : "Find & Book"}
        </button>
      </form>
      <div className="flex flex-wrap gap-2 justify-center mb-5">
        {EXAMPLES.map((e) => (
          <button key={e} onClick={() => run(e)} disabled={loading} className="text-[11px] text-violet-600 bg-violet-50 rounded-full px-3 py-1">{e}</button>
        ))}
      </div>

      {error && (
        <div className="flex items-start gap-2 bg-red-50 border border-red-100 text-red-600 text-sm rounded-xl px-4 py-3 mb-4">
          <AlertCircle size={16} className="mt-0.5 shrink-0" /><span>{error}</span>
        </div>
      )}

      {result && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col gap-3">
          <div className="flex items-center justify-between text-[11px] text-gray-400 px-1">
            <span>Agent execution trace</span><span>{result.total_ms} ms total</span>
          </div>
          {result.trace.map((t, i) => <TraceRow key={i} step={t} />)}

          <div className={`rounded-2xl border p-4 text-sm ${toneCls[tone]}`}>
            <div className="flex items-center gap-2 font-semibold mb-1">
              {s === "confirmed" || confirmedId ? <CheckCircle2 size={16} /> : s === "needs_info" ? <HelpCircle size={16} />
                : s === "escalated" ? <ShieldAlert size={16} /> : <AlertCircle size={16} />}
              {confirmedId ? "Booking confirmed" : heading[s ?? "escalated"]}
            </div>
            <div className="text-xs">{result.message}</div>
            {s === "confirmed" && <div className="text-xs mt-2">{result.email_sent ? "Confirmation email sent with PDF receipt." : "Booking saved. Email was not sent."}</div>}
            {s === "confirmed" && <div className="text-[11px] opacity-80 mt-2">{result.resource_name} · ID {result.booking_id}</div>}

            {result.proposal && !confirmedId && (
              <div className="mt-3 pt-3 border-t border-current/10">
                <div className="flex items-center gap-2 text-xs font-medium mb-2">
                  <Clock size={13} /> {fmt(result.proposal.slot_start)} – {fmt(result.proposal.slot_end)} · {result.resource_name}
                  {result.decision_source === "deterministic_fallback" && <span className="badge bg-amber-100 text-amber-700">rule-based pick</span>}
                </div>
                {s === "needs_confirmation" ? (
                  <button onClick={confirm} disabled={confirming}
                    className="gradient-btn text-white rounded-lg px-3 py-1.5 text-xs font-medium flex items-center gap-1.5">
                    {confirming ? <Loader2 size={12} className="animate-spin" /> : <Check size={12} />} Confirm this slot
                  </button>
                ) : (
                  <div className="text-[11px] opacity-80">Its booking window opens 30 minutes before the slot. Come back then to book it.</div>
                )}
                {confirmError && <div className="text-[11px] text-red-600 mt-2">{confirmError}</div>}
              </div>
            )}
            {confirmedId && <div className="text-[11px] opacity-80 mt-2">ID {confirmedId}</div>}
          </div>

          {result.candidates.length > 0 && (
            <details className="text-[11px] text-gray-500 px-1">
              <summary className="cursor-pointer">Candidates the agent evaluated ({result.candidates.length})</summary>
              <div className="mt-2 flex flex-col gap-1">
                {result.candidates.map((c) => (
                  <div key={c.candidate_id} className="soft-card rounded-lg px-3 py-2 flex justify-between">
                    <span>{fmt(c.start)} – {fmt(c.end)}</span>
                    <span>{c.usable_minutes} min · {c.bookable_now ? "bookable now" : `opens ${c.opens_at}`}{c.back_to_back ? " · back-to-back" : ""}</span>
                  </div>
                ))}
              </div>
            </details>
          )}
        </motion.div>
      )}
    </div>
  );
}
