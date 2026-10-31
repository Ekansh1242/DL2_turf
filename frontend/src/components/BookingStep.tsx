import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CalendarDays, Clock, CheckCircle2, AlertCircle, Loader2, Trophy, ChevronLeft,
  Download, Mail, ListChecks, XCircle, Bell,
} from "lucide-react";
import {
  listSports, listSlots, confirmBooking, downloadReceipt, myBookings, cancelBooking, joinWaitlist,
  Sport, Slot, ConfirmBookingResult, MyBooking,
} from "../api/client";

function nextNDays(n: number): Date[] {
  const out: Date[] = [];
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  for (let i = 0; i < n; i++) {
    const d = new Date(today);
    d.setDate(today.getDate() + i);
    out.push(d);
  }
  return out;
}

function formatDay(d: Date) {
  return d.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" });
}

function toLocalDateParam(d: Date) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

function slotStatusLabel(s: Slot): string | null {
  if (s.is_booked) return "Booked";
  if (!s.is_bookable_now) {
    const opens = new Date(s.window_opens_at);
    const now = new Date();
    if (opens > now) {
      return `Opens ${opens.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}`;
    }
    return "Ended";
  }
  return null;
}

type Step = "sport" | "date" | "slot" | "result" | "mine";

function MyBookingsView({ token, onBack }: { token: string; onBack: () => void }) {
  const [bookings, setBookings] = useState<MyBooking[]>([]);
  const [loading, setLoading] = useState(true);
  const [cancellingId, setCancellingId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  function load() {
    setLoading(true);
    myBookings(token).then(setBookings).finally(() => setLoading(false));
  }

  useEffect(load, [token]);

  async function handleCancel(id: string) {
    setCancellingId(id);
    setMessage(null);
    try {
      const res = await cancelBooking(id, token);
      setMessage(res.message);
      load();
    } finally {
      setCancellingId(null);
    }
  }

  const statusColor: Record<string, string> = {
    confirmed: "text-emerald-600 bg-emerald-50 border-emerald-200",
    cancelled: "text-gray-400 bg-gray-50 border-gray-200",
    no_show: "text-red-600 bg-red-50 border-red-200",
    completed: "text-gray-500 bg-gray-50 border-gray-200",
  };

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <button onClick={onBack} className="flex items-center gap-1 text-xs text-gray-500 mb-3 hover:text-violet-600">
        <ChevronLeft size={14} /> Back
      </button>
      {message && (
        <div className="text-xs bg-violet-50 border border-violet-100 text-violet-700 rounded-xl px-3 py-2 mb-3">{message}</div>
      )}
      {loading && <div className="flex justify-center py-8 text-gray-400"><Loader2 className="animate-spin" /></div>}
      <div className="flex flex-col gap-2">
        {bookings.map((b) => (
          <div key={b.id} className="glass-card rounded-xl p-3 text-sm">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium capitalize">{b.sport.replace("_", " ")}</div>
                <div className="text-xs text-gray-500">
                  {new Date(b.start_time).toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" })}
                  {" · "}
                  {new Date(b.start_time).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}
                </div>
              </div>
              <span className={`text-[10px] font-medium rounded-full px-2 py-0.5 border ${statusColor[b.status] ?? ""}`}>
                {b.status.replace("_", " ")}
              </span>
            </div>
            {b.status === "confirmed" && (
              <div className="mt-2 flex items-center justify-between">
                <span className="text-[11px] text-gray-400">
                  Cancel by {new Date(b.cancel_deadline).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}
                </span>
                <button
                  onClick={() => handleCancel(b.id)}
                  disabled={!b.can_cancel || cancellingId === b.id}
                  className="text-xs flex items-center gap-1 text-red-600 disabled:text-gray-300 font-medium"
                >
                  {cancellingId === b.id ? <Loader2 size={12} className="animate-spin" /> : <XCircle size={12} />}
                  Cancel
                </button>
              </div>
            )}
          </div>
        ))}
        {!loading && bookings.length === 0 && (
          <div className="text-center text-sm text-gray-400 py-8">No bookings yet.</div>
        )}
      </div>
    </motion.div>
  );
}

export default function BookingStep({ token }: { token: string }) {
  const [step, setStep] = useState<Step>("sport");
  const [sports, setSports] = useState<Sport[]>([]);
  const [selectedSport, setSelectedSport] = useState<Sport | null>(null);
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [selectedSlot, setSelectedSlot] = useState<Slot | null>(null);
  const [result, setResult] = useState<ConfirmBookingResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [waitlistedSlot, setWaitlistedSlot] = useState<string | null>(null);
  const [waitlistMessage, setWaitlistMessage] = useState<string | null>(null);

  const days = nextNDays(7);

  useEffect(() => {
    listSports(token).then(setSports).catch(() => setSports([]));
  }, [token]);

  async function handleJoinWaitlist(slot: Slot) {
    if (!selectedSport) return;
    setWaitlistedSlot(slot.slot_start);
    setWaitlistMessage(null);
    try {
      const res = await joinWaitlist(selectedSport.resource_id, slot.slot_start, slot.slot_end, token);
      setWaitlistMessage(res.message);
    } finally {
      setWaitlistedSlot(null);
    }
  }

  async function pickDate(d: Date) {
    if (!selectedSport) return;
    setSelectedDate(d);
    setLoading(true);
    try {
      const s = await listSlots(selectedSport.resource_id, toLocalDateParam(d), token);
      setSlots(s);
      setStep("slot");
    } finally {
      setLoading(false);
    }
  }

  async function pickSlot(slot: Slot) {
    if (!selectedSport) return;
    setSelectedSlot(slot);
    setLoading(true);
    try {
      const res = await confirmBooking(selectedSport.resource_id, slot.slot_start, slot.slot_end, token);
      setResult(res);
      setStep("result");
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setStep("sport");
    setSelectedSport(null);
    setSelectedDate(null);
    setSlots([]);
    setSelectedSlot(null);
    setResult(null);
  }

  function back() {
    if (step === "date") setStep("sport");
    else if (step === "slot") setStep("date");
  }

  async function handleDownload() {
    if (!result?.booking_id) return;
    setDownloading(true);
    try {
      await downloadReceipt(result.booking_id, token);
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="min-h-screen px-4 py-10 max-w-lg mx-auto">
      <div className="flex items-center gap-2 justify-center mb-1">
        <Trophy size={20} className="text-violet-600" />
        <h2 className="text-xl font-bold gradient-text">Book a Slot</h2>
      </div>
      <p className="text-xs text-gray-500 text-center mb-4">
        Pick a sport, a day, and an open time slot.
      </p>

      {step !== "mine" && (
        <button
          onClick={() => setStep("mine")}
          className="flex items-center gap-1.5 justify-center text-xs text-violet-600 font-medium mb-4 mx-auto"
        >
          <ListChecks size={13} /> My Bookings
        </button>
      )}

      {step === "mine" ? (
        <MyBookingsView token={token} onBack={() => setStep("sport")} />
      ) : (
      <>
      {step !== "sport" && step !== "result" && (
        <button onClick={back} className="flex items-center gap-1 text-xs text-gray-500 mb-3 hover:text-violet-600">
          <ChevronLeft size={14} /> Back
        </button>
      )}

      <AnimatePresence mode="wait">
        {step === "sport" && (
          <motion.div key="sport" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="grid grid-cols-2 gap-3">
            {sports.map((s) => (
              <button key={s.resource_id} onClick={() => { setSelectedSport(s); setStep("date"); }}
                className="glass-card rounded-2xl p-4 text-left shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all">
                <div className="w-9 h-9 rounded-xl gradient-btn flex items-center justify-center text-white mb-2">
                  <Trophy size={16} />
                </div>
                <div className="text-sm font-semibold capitalize">{s.sport}</div>
                <div className="text-xs text-gray-500">{s.resource_name}</div>
              </button>
            ))}
            {sports.length === 0 && (
              <div className="col-span-2 text-center text-sm text-gray-400 py-8">Loading sports...</div>
            )}
          </motion.div>
        )}

        {step === "date" && (
          <motion.div key="date" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="flex flex-col gap-2">
            {days.map((d) => (
              <button key={d.toISOString()} onClick={() => pickDate(d)} disabled={loading}
                className="glass-card rounded-xl p-3 flex items-center gap-3 text-left shadow-sm hover:shadow-md transition-all disabled:opacity-50">
                <div className="w-8 h-8 rounded-lg gradient-btn flex items-center justify-center text-white shrink-0">
                  <CalendarDays size={14} />
                </div>
                <span className="text-sm font-medium">{formatDay(d)}</span>
                {loading && <Loader2 size={14} className="animate-spin ml-auto text-violet-500" />}
              </button>
            ))}
          </motion.div>
        )}

        {step === "slot" && (
          <motion.div key="slot" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            {slots.every((s) => s.is_booked || !s.is_bookable_now) && slots.length > 0 && (
              <div className="text-center text-xs text-amber-600 bg-amber-50 border border-amber-100 rounded-xl px-3 py-2 mb-3">
                No slots open right now — each slot's booking window opens 30 minutes before it starts.
              </div>
            )}
            {waitlistMessage && (
              <div className="text-center text-xs text-violet-700 bg-violet-50 border border-violet-100 rounded-xl px-3 py-2 mb-3 flex items-center gap-1.5 justify-center">
                <Bell size={12} /> {waitlistMessage}
              </div>
            )}
            <div className="grid grid-cols-2 gap-3">
              {slots.map((s) => {
                const statusLabel = slotStatusLabel(s);
                const disabled = s.is_booked || !s.is_bookable_now || loading;
                return (
                  <div key={s.slot_start} className="flex flex-col gap-1">
                    <button
                      disabled={disabled}
                      onClick={() => pickSlot(s)}
                      className={`glass-card rounded-xl p-3 text-sm flex flex-col gap-1 shadow-sm transition-all w-full ${
                        s.is_booked
                          ? "bg-red-50 border border-red-200 text-red-500 cursor-not-allowed"
                          : !s.is_bookable_now
                          ? "opacity-40 cursor-not-allowed"
                          : "hover:shadow-md hover:-translate-y-0.5"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <Clock size={14} className={s.is_booked ? "text-red-400 shrink-0" : "text-violet-500 shrink-0"} />
                        <span>{formatTime(s.slot_start)}</span>
                      </div>
                      {statusLabel && (
                        <span className={`text-[11px] ml-6 ${s.is_booked ? "text-red-500" : "text-gray-500"}`}>{statusLabel}</span>
                      )}
                    </button>
                    {s.is_booked && (
                      <button
                        onClick={() => handleJoinWaitlist(s)}
                        disabled={waitlistedSlot === s.slot_start}
                        className="text-[11px] text-violet-600 flex items-center justify-center gap-1 py-1"
                      >
                        {waitlistedSlot === s.slot_start ? <Loader2 size={11} className="animate-spin" /> : <Bell size={11} />}
                        Join waitlist
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
            {slots.length === 0 && !loading && (
              <div className="text-center text-sm text-gray-400 py-8">No slots for this day.</div>
            )}
          </motion.div>
        )}

        {step === "result" && result && (
          <motion.div key="result" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
            className={`rounded-2xl p-4 text-sm ${
              result.success
                ? "bg-emerald-50 border border-emerald-200 text-emerald-700"
                : "bg-amber-50 border border-amber-200 text-amber-700"
            }`}>
            <div className="flex items-center gap-2 font-semibold mb-1">
              {result.success ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
              {result.success ? "Booking Confirmed" : "Couldn't Book"}
            </div>
            {result.success && result.booking_id && (
              <div className="text-xs opacity-80 mt-1">Booking ID: {result.booking_id}</div>
            )}
            <div className="text-xs mt-1">{result.message}</div>
            {result.success && (
              <div className="flex items-center gap-1.5 text-xs mt-2 opacity-80">
                <Mail size={12} />
                {result.email_sent
                  ? "Confirmation emailed to you."
                  : "Email confirmation unavailable — download the receipt below instead."}
              </div>
            )}
            {result.success && result.booking_id && (
              <button onClick={handleDownload} disabled={downloading}
                className="flex items-center justify-center gap-2 bg-white border border-emerald-200 text-emerald-700 rounded-xl py-2 text-xs font-medium w-full mt-3 disabled:opacity-60">
                {downloading ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
                Download PDF Receipt
              </button>
            )}
            <button onClick={reset} className="gradient-btn text-white rounded-xl py-2 text-xs font-medium w-full mt-2">
              Book another slot
            </button>
          </motion.div>
        )}
      </AnimatePresence>
      </>
      )}
    </div>
  );
}
