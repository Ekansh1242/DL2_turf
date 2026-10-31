import { useState } from "react";
import { motion } from "framer-motion";
import { Mail, User, Hash, Building2, GraduationCap, ArrowRight, Loader2, Trophy, ShieldCheck, CalendarClock } from "lucide-react";
import { login } from "../api/client";

export default function LoginStep({ onLoggedIn }: { onLoggedIn: (token: string, role: string) => void }) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [rollNo, setRollNo] = useState("");
  const [department, setDepartment] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await login(email, name, rollNo, department || undefined);
      onLoggedIn(res.access_token, res.role);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-4xl grid md:grid-cols-2 gap-8 items-center">
        <motion.div
          initial={{ opacity: 0, x: -16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
          className="hidden md:flex flex-col gap-6 pr-4"
        >
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-10 h-10 rounded-xl gradient-btn flex items-center justify-center text-white">
                <GraduationCap size={20} />
              </div>
              <span className="text-2xl font-extrabold gradient-text">CampusSphere AI</span>
            </div>
            <p className="text-sm text-gray-500 max-w-xs">
              Book turfs and courts across campus, get instant confirmations, and never lose a slot to double-booking.
            </p>
          </div>
          <div className="flex flex-col gap-3">
            {[
              { icon: <Trophy size={15} />, text: "8 sports, one dedicated turf each" },
              { icon: <CalendarClock size={15} />, text: "Live slot availability, first-come first-served" },
              { icon: <ShieldCheck size={15} />, text: "Restricted to verified RCOEM accounts" },
            ].map((item) => (
              <div key={item.text} className="flex items-center gap-3 text-sm text-gray-600">
                <div className="w-8 h-8 rounded-lg bg-violet-50 text-violet-600 flex items-center justify-center shrink-0">
                  {item.icon}
                </div>
                {item.text}
              </div>
            ))}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="glass-card rounded-2xl shadow-xl p-8 w-full max-w-sm mx-auto"
        >
          <div className="flex items-center gap-2 mb-1 md:hidden">
            <div className="w-9 h-9 rounded-xl gradient-btn flex items-center justify-center text-white">
              <GraduationCap size={18} />
            </div>
            <h1 className="text-xl font-extrabold gradient-text">CampusSphere AI</h1>
          </div>
          <h2 className="hidden md:block text-lg font-bold text-gray-800 mb-1">Sign in</h2>
          <p className="text-xs text-gray-400 mb-5">RCOEM students &amp; staff only</p>

          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <div className="relative">
              <Mail size={16} className="absolute left-3 top-3 text-gray-400" />
              <input className="input-field pl-9"
                placeholder="College email (you@rknec.edu)" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            <div className="relative">
              <User size={16} className="absolute left-3 top-3 text-gray-400" />
              <input className="input-field pl-9"
                placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div className="relative">
              <Hash size={16} className="absolute left-3 top-3 text-gray-400" />
              <input className="input-field pl-9"
                placeholder="Roll number" value={rollNo} onChange={(e) => setRollNo(e.target.value)} required />
            </div>
            <div className="relative">
              <Building2 size={16} className="absolute left-3 top-3 text-gray-400" />
              <input className="input-field pl-9"
                placeholder="Department" value={department} onChange={(e) => setDepartment(e.target.value)} required />
            </div>
            <button type="submit" disabled={loading}
              className="gradient-btn text-white rounded-xl py-2.5 text-sm font-medium flex items-center justify-center gap-2 mt-1">
              {loading ? <Loader2 size={16} className="animate-spin" /> : <ArrowRight size={16} />}
              {loading ? "Signing in..." : "Continue"}
            </button>
          </form>
          {error && <p className="text-red-500 mt-3 text-xs bg-red-50 border border-red-100 rounded-lg px-3 py-2">{error}</p>}
        </motion.div>
      </div>
    </div>
  );
}
