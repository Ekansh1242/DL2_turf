import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  LayoutDashboard, UserPlus, FileDown, Loader2, Search, CheckCircle2,
  AlertCircle, Users, CalendarCheck, XCircle, IndianRupee, TrendingUp,
  ClipboardList, QrCode, ShieldAlert, Sparkles, Send,
} from "lucide-react";
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import {
  adminSummary, adminTrend, adminBySport, adminByDepartment, adminPeakHours, adminTopStudents,
  adminSearchStudents, adminBookFor, downloadBookingsCsv, downloadSummaryPdf,
  adminEquipmentIssues, adminFinesByStudent, adminTodaysBookings, adminCheckIn, adminMarkNoShow,
  listSports, listSlots, askAnalytics, AnalyticsAnswer,
  SummaryOut, TrendPoint, SportBreakdown, DeptBreakdown, PeakHour, TopStudent,
  StudentOut, Sport, Slot, EquipmentIssueBreakdown, StudentFine, TodayBooking,
} from "../api/client";

type Tab = "dashboard" | "ask" | "book-for" | "today" | "reports";

function StatCard({ label, value, icon, accent }: { label: string; value: string | number; icon: JSX.Element; accent?: string }) {
  return (
    <motion.div whileHover={{ y: -2 }} className="soft-card rounded-2xl p-4">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center mb-2 ${accent ?? "bg-violet-50 text-violet-600"}`}>
        {icon}
      </div>
      <div className="text-2xl font-bold text-gray-800">{value}</div>
      <div className="text-xs text-gray-400 mt-0.5">{label}</div>
    </motion.div>
  );
}

function DashboardTab({ token }: { token: string }) {
  const [summary, setSummary] = useState<SummaryOut | null>(null);
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const [bySport, setBySport] = useState<SportBreakdown[]>([]);
  const [byDept, setByDept] = useState<DeptBreakdown[]>([]);
  const [peakHours, setPeakHours] = useState<PeakHour[]>([]);
  const [topStudents, setTopStudents] = useState<TopStudent[]>([]);
  const [equipmentIssues, setEquipmentIssues] = useState<EquipmentIssueBreakdown[]>([]);
  const [finesByStudent, setFinesByStudent] = useState<StudentFine[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      adminSummary(token), adminTrend(token), adminBySport(token),
      adminByDepartment(token), adminPeakHours(token), adminTopStudents(token),
      adminEquipmentIssues(token), adminFinesByStudent(token),
    ]).then(([s, t, sp, d, p, top, eq, fines]) => {
      setSummary(s); setTrend(t); setBySport(sp); setByDept(d); setPeakHours(p);
      setTopStudents(top); setEquipmentIssues(eq); setFinesByStudent(fines);
    }).finally(() => setLoading(false));
  }, [token]);

  if (loading) return <div className="flex justify-center py-16 text-gray-400"><Loader2 className="animate-spin" /></div>;

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="Total bookings" value={summary?.total_bookings ?? 0} icon={<CalendarCheck size={16} />} accent="bg-violet-50 text-violet-600" />
        <StatCard label="No-shows" value={summary?.no_shows ?? 0} icon={<XCircle size={16} />} accent="bg-red-50 text-red-500" />
        <StatCard label="Unique students" value={summary?.unique_students ?? 0} icon={<Users size={16} />} accent="bg-blue-50 text-blue-600" />
        <StatCard label="Fines collected" value={`Rs.${summary?.total_fines_rupees ?? 0}`} icon={<IndianRupee size={16} />} accent="bg-amber-50 text-amber-600" />
      </div>

      <div className="glass-card rounded-xl p-4">
        <div className="flex items-center gap-2 text-sm font-medium mb-3"><TrendingUp size={14} className="text-violet-600" /> Booking trend (30 days)</div>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={trend}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
            <Tooltip />
            <Line type="monotone" dataKey="count" stroke="#7c3aed" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        <div className="glass-card rounded-xl p-4">
          <div className="text-sm font-medium mb-3">Bookings by sport</div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={bySport}>
              <XAxis dataKey="sport" tick={{ fontSize: 9 }} interval={0} angle={-20} textAnchor="end" height={50} />
              <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#7c3aed" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="glass-card rounded-xl p-4">
          <div className="text-sm font-medium mb-3">Peak hours</div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={peakHours}>
              <XAxis dataKey="hour" tick={{ fontSize: 10 }} tickFormatter={(h) => `${h}:00`} />
              <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
              <Tooltip labelFormatter={(h) => `${h}:00`} />
              <Bar dataKey="count" fill="#4f46e5" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        <div className="glass-card rounded-xl p-4">
          <div className="text-sm font-medium mb-3">By department</div>
          <div className="flex flex-col gap-2">
            {byDept.map((d) => (
              <div key={d.department} className="flex justify-between text-xs">
                <span className="text-gray-600">{d.department}</span>
                <span className="font-semibold">{d.count}</span>
              </div>
            ))}
            {byDept.length === 0 && <p className="text-xs text-gray-400">No data yet.</p>}
          </div>
        </div>

        <div className="glass-card rounded-xl p-4">
          <div className="text-sm font-medium mb-3">Top students</div>
          <div className="flex flex-col gap-2">
            {topStudents.map((s) => (
              <div key={s.email} className="flex justify-between text-xs">
                <span className="text-gray-600">{s.name}</span>
                <span className="font-semibold">{s.booking_count}</span>
              </div>
            ))}
            {topStudents.length === 0 && <p className="text-xs text-gray-400">No data yet.</p>}
          </div>
        </div>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        <div className="glass-card rounded-xl p-4">
          <div className="flex items-center gap-2 text-sm font-medium mb-3">
            <ShieldAlert size={14} className="text-red-500" /> Equipment issues
          </div>
          <div className="flex flex-col gap-2">
            {equipmentIssues.map((e) => (
              <div key={e.equipment_name} className="flex justify-between items-center text-xs">
                <span className="text-gray-600">{e.equipment_name}</span>
                <span className="flex items-center gap-2">
                  {e.damaged_count > 0 && <span className="text-amber-600">{e.damaged_count} damaged</span>}
                  {e.lost_count > 0 && <span className="text-red-500">{e.lost_count} lost</span>}
                  <span className="font-semibold">Rs.{e.total_fines_rupees}</span>
                </span>
              </div>
            ))}
            {equipmentIssues.length === 0 && <p className="text-xs text-gray-400">No fines recorded yet.</p>}
          </div>
        </div>

        <div className="glass-card rounded-xl p-4">
          <div className="flex items-center gap-2 text-sm font-medium mb-3">
            <IndianRupee size={14} className="text-amber-600" /> Fines by student
          </div>
          <div className="flex flex-col gap-2">
            {finesByStudent.map((f) => (
              <div key={f.email} className="flex justify-between text-xs">
                <span className="text-gray-600">{f.name}</span>
                <span className="font-semibold">Rs.{f.total_fines_rupees}</span>
              </div>
            ))}
            {finesByStudent.length === 0 && <p className="text-xs text-gray-400">No fines recorded yet.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}

function BookForStudentTab({ token }: { token: string }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<StudentOut[]>([]);
  const [selectedStudent, setSelectedStudent] = useState<StudentOut | null>(null);
  const [sports, setSports] = useState<Sport[]>([]);
  const [selectedSport, setSelectedSport] = useState<Sport | null>(null);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [message, setMessage] = useState<{ type: "ok" | "err"; text: string } | null>(null);
  const [booking, setBooking] = useState(false);

  useEffect(() => { listSports(token).then(setSports); }, [token]);

  async function handleSearch() {
    if (!query.trim()) return;
    const res = await adminSearchStudents(query, token);
    setResults(res);
  }

  async function handleSelectSport(sport: Sport) {
    setSelectedSport(sport);
    const today = new Date().toISOString();
    const s = await listSlots(sport.resource_id, today, token);
    setSlots(s);
  }

  async function handleBook(slot: Slot) {
    if (!selectedStudent || !selectedSport) return;
    setBooking(true);
    setMessage(null);
    try {
      const res = await adminBookFor(selectedStudent.id, selectedSport.resource_id, slot.slot_start, slot.slot_end, token);
      setMessage({
        type: res.success ? "ok" : "err",
        text: res.success
          ? `Booked for ${selectedStudent.name}.${res.email_sent ? " Confirmation emailed." : ""}`
          : res.message,
      });
    } catch (err) {
      setMessage({ type: "err", text: err instanceof Error ? err.message : "Booking failed" });
    } finally {
      setBooking(false);
    }
  }

  return (
    <div className="flex flex-col gap-4 max-w-lg">
      <div className="glass-card rounded-xl p-4">
        <div className="text-sm font-medium mb-2">1. Find the student</div>
        <div className="flex gap-2">
          <input
            className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white/70 focus:outline-none focus:ring-2 focus:ring-violet-400"
            placeholder="Name, roll number, or email"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
          <button onClick={handleSearch} className="gradient-btn text-white rounded-lg px-3 flex items-center"><Search size={16} /></button>
        </div>
        {results.length > 0 && (
          <div className="mt-2 flex flex-col gap-1">
            {results.map((s) => (
              <button
                key={s.id}
                onClick={() => setSelectedStudent(s)}
                disabled={s.is_blocked}
                className={`text-left text-xs rounded-lg px-3 py-2 border ${
                  selectedStudent?.id === s.id ? "border-violet-400 bg-violet-50" : "border-gray-100"
                } ${s.is_blocked ? "opacity-40" : "hover:bg-gray-50"}`}
              >
                {s.name} &middot; {s.roll_no || "no roll no"} &middot; {s.department || "-"}
                {s.is_blocked && " (blocked)"}
              </button>
            ))}
          </div>
        )}
      </div>

      {selectedStudent && (
        <div className="glass-card rounded-xl p-4">
          <div className="text-sm font-medium mb-2">2. Choose sport</div>
          <div className="flex flex-wrap gap-2">
            {sports.map((sp) => (
              <button
                key={sp.resource_id}
                onClick={() => handleSelectSport(sp)}
                className={`text-xs rounded-lg px-3 py-1.5 border ${
                  selectedSport?.resource_id === sp.resource_id ? "border-violet-400 bg-violet-50" : "border-gray-100"
                }`}
              >
                {sp.sport.replace("_", " ")}
              </button>
            ))}
          </div>
        </div>
      )}

      {selectedSport && (
        <div className="glass-card rounded-xl p-4">
          <div className="text-sm font-medium mb-2">3. Pick a slot (today)</div>
          <div className="grid grid-cols-3 gap-2">
            {slots.map((slot) => (
              <button
                key={slot.slot_start}
                disabled={slot.is_booked || booking}
                onClick={() => handleBook(slot)}
                className={`text-xs rounded-lg px-2 py-2 border ${
                  slot.is_booked
                    ? "bg-red-50 border-red-200 text-red-500 cursor-not-allowed"
                    : "hover:bg-gray-50 border-gray-100"
                }`}
              >
                {new Date(slot.slot_start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </button>
            ))}
          </div>
        </div>
      )}

      {message && (
        <div className={`rounded-xl p-3 text-sm flex items-center gap-2 ${
          message.type === "ok" ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "bg-red-50 text-red-600 border border-red-100"
        }`}>
          {message.type === "ok" ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
          {message.text}
        </div>
      )}
    </div>
  );
}

function TodaysBookingsTab({ token }: { token: string }) {
  const [bookings, setBookings] = useState<TodayBooking[]>([]);
  const [loading, setLoading] = useState(true);
  const [actingId, setActingId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  function load() {
    setLoading(true);
    adminTodaysBookings(token).then(setBookings).finally(() => setLoading(false));
  }

  useEffect(load, [token]);

  async function handleCheckIn(id: string) {
    setActingId(id);
    setMessage(null);
    try {
      const res = await adminCheckIn(id, token);
      setMessage(res.message);
      load();
    } finally {
      setActingId(null);
    }
  }

  async function handleNoShow(id: string) {
    setActingId(id);
    setMessage(null);
    try {
      const res = await adminMarkNoShow(id, token);
      setMessage(res.message);
      load();
    } finally {
      setActingId(null);
    }
  }

  const statusStyle: Record<string, string> = {
    confirmed: "bg-white",
    cancelled: "bg-gray-50 opacity-60",
    no_show: "bg-red-50 border-red-200",
    completed: "bg-gray-50 opacity-60",
  };

  return (
    <div className="max-w-2xl">
      <div className="flex items-center gap-2 text-sm font-medium mb-3">
        <ClipboardList size={14} className="text-violet-600" /> Today's bookings
      </div>
      {message && (
        <div className="text-xs bg-violet-50 border border-violet-100 text-violet-700 rounded-xl px-3 py-2 mb-3">{message}</div>
      )}
      {loading && <div className="flex justify-center py-8 text-gray-400"><Loader2 className="animate-spin" /></div>}
      <div className="flex flex-col gap-2">
        {bookings.map((b) => (
          <div key={b.booking_id} className={`glass-card rounded-xl p-3 text-sm border ${statusStyle[b.status] ?? ""}`}>
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">{b.student_name}</div>
                <div className="text-xs text-gray-500">
                  {b.resource_name} &middot; {new Date(b.start_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  {" - "}
                  {new Date(b.end_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {b.checked_in && (
                  <span className="text-[10px] text-emerald-600 flex items-center gap-1"><QrCode size={11} /> Checked in</span>
                )}
                {b.status === "no_show" && (
                  <span className="text-[10px] text-red-500 font-medium">No-show</span>
                )}
                {b.status === "confirmed" && !b.checked_in && (
                  <>
                    <button
                      onClick={() => handleCheckIn(b.booking_id)}
                      disabled={actingId === b.booking_id}
                      className="text-[11px] gradient-btn text-white rounded-lg px-2 py-1 flex items-center gap-1"
                    >
                      {actingId === b.booking_id ? <Loader2 size={11} className="animate-spin" /> : <QrCode size={11} />}
                      Check in
                    </button>
                    <button
                      onClick={() => handleNoShow(b.booking_id)}
                      disabled={actingId === b.booking_id}
                      className="text-[11px] text-red-600 border border-red-200 rounded-lg px-2 py-1"
                    >
                      No-show
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        ))}
        {!loading && bookings.length === 0 && (
          <div className="text-center text-sm text-gray-400 py-8">No bookings today.</div>
        )}
      </div>
    </div>
  );
}

function ReportsTab({ token }: { token: string }) {
  const [downloading, setDownloading] = useState<string | null>(null);

  async function handle(kind: "csv" | "pdf") {
    setDownloading(kind);
    try {
      if (kind === "csv") await downloadBookingsCsv(token);
      else await downloadSummaryPdf(token);
    } finally {
      setDownloading(null);
    }
  }

  return (
    <div className="flex flex-col gap-4 max-w-md">
      <button
        onClick={() => handle("pdf")}
        disabled={downloading !== null}
        className="glass-card rounded-xl p-4 flex items-center justify-between hover:bg-gray-50 text-left"
      >
        <div>
          <div className="text-sm font-medium">Summary report (PDF)</div>
          <div className="text-xs text-gray-500">Charts + breakdowns, college letterhead</div>
        </div>
        {downloading === "pdf" ? <Loader2 size={16} className="animate-spin" /> : <FileDown size={16} className="text-violet-600" />}
      </button>
      <button
        onClick={() => handle("csv")}
        disabled={downloading !== null}
        className="glass-card rounded-xl p-4 flex items-center justify-between hover:bg-gray-50 text-left"
      >
        <div>
          <div className="text-sm font-medium">Full bookings export (CSV)</div>
          <div className="text-xs text-gray-500">Every booking, filterable in Excel/Sheets</div>
        </div>
        {downloading === "csv" ? <Loader2 size={16} className="animate-spin" /> : <FileDown size={16} className="text-violet-600" />}
      </button>
    </div>
  );
}

function AskAITab({ token }: { token: string }) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalyticsAnswer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const examples = ["Which sport has the most bookings?", "What are the peak booking hours?", "Which equipment gets damaged most?"];

  async function ask(q: string) {
    if (!q.trim()) return;
    setQuestion(q); setLoading(true); setError(null); setResult(null);
    try { setResult(await askAnalytics(q, token)); }
    catch (e) { setError(e instanceof Error ? e.message : "Something went wrong"); }
    finally { setLoading(false); }
  }

  return (
    <div className="max-w-xl flex flex-col gap-4">
      <div className="glass-card rounded-xl p-4">
        <div className="flex gap-2">
          <input className="input-field" placeholder="Ask about bookings, usage, fines..." value={question}
            onChange={(e) => setQuestion(e.target.value)} onKeyDown={(e) => e.key === "Enter" && ask(question)} />
          <button onClick={() => ask(question)} disabled={loading} className="gradient-btn text-white rounded-xl px-3">
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
          </button>
        </div>
        <div className="flex flex-wrap gap-2 mt-3">
          {examples.map((e) => (
            <button key={e} onClick={() => ask(e)} className="text-[11px] text-violet-600 bg-violet-50 rounded-full px-3 py-1">{e}</button>
          ))}
        </div>
      </div>
      {error && <div className="text-xs bg-red-50 border border-red-100 text-red-600 rounded-xl px-3 py-2">{error}</div>}
      {result && (
        <div className="glass-card rounded-xl p-4">
          <div className="text-sm text-gray-800">{result.answer}</div>
          <div className="mt-3 pt-3 border-t border-gray-100 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-gray-400">
            <span>Read-only query: <b className="text-gray-600">{result.tool}</b></span>
            {result.trace.map((t) => <span key={t.node}>{t.node} · {t.duration_ms} ms</span>)}
          </div>
          <details className="mt-2 text-[11px] text-gray-500">
            <summary className="cursor-pointer">Data behind this answer</summary>
            <pre className="mt-1 overflow-x-auto bg-gray-50 rounded-lg p-2">{JSON.stringify(result.data, null, 2)}</pre>
          </details>
        </div>
      )}
    </div>
  );
}

export default function AdminHome({ token }: { token: string }) {
  const [tab, setTab] = useState<Tab>("dashboard");

  const tabs: { id: Tab; label: string; icon: JSX.Element }[] = [
    { id: "dashboard", label: "Dashboard", icon: <LayoutDashboard size={14} /> },
    { id: "ask", label: "Ask AI", icon: <Sparkles size={14} /> },
    { id: "book-for", label: "Book for Student", icon: <UserPlus size={14} /> },
    { id: "today", label: "Today", icon: <ClipboardList size={14} /> },
    { id: "reports", label: "Reports", icon: <FileDown size={14} /> },
  ];

  return (
    <div className="min-h-screen px-4 py-8 max-w-3xl mx-auto">
      <h1 className="text-xl font-bold gradient-text mb-1">Sports Department</h1>
      <p className="text-xs text-gray-500 mb-6">Live analytics, staff bookings, and reports.</p>

      <div className="flex gap-2 mb-6">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-1.5 text-xs font-medium rounded-full px-3 py-1.5 transition-colors ${
              tab === t.id ? "gradient-btn text-white" : "glass-card text-gray-600"
            }`}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      <motion.div key={tab} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
        {tab === "dashboard" && <DashboardTab token={token} />}
        {tab === "ask" && <AskAITab token={token} />}
        {tab === "book-for" && <BookForStudentTab token={token} />}
        {tab === "today" && <TodaysBookingsTab token={token} />}
        {tab === "reports" && <ReportsTab token={token} />}
      </motion.div>
    </div>
  );
}
