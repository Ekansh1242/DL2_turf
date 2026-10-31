import { useState } from "react";
import LoginStep from "./components/LoginStep";
import BookingStep from "./components/BookingStep";
import AIBookingStep from "./components/AIBookingStep";
import AdminHome from "./components/AdminHome";
import TopNav from "./components/TopNav";

export default function App() {
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [mode, setMode] = useState<"manual" | "ai">("manual");

  if (!token || !role) {
    return <LoginStep onLoggedIn={(t, r) => { setToken(t); setRole(r); }} />;
  }

  function handleLogout() {
    setToken(null);
    setRole(null);
    setMode("manual");
  }

  return (
    <div>
      <TopNav role={role} onLogout={handleLogout} />
      {role === "admin" ? (
        <AdminHome token={token} />
      ) : (
        <>
          <div className="flex justify-center gap-2 pt-4">
            {(["manual", "ai"] as const).map((m) => (
              <button key={m} onClick={() => setMode(m)}
                className={`text-xs font-medium rounded-full px-4 py-1.5 transition-colors ${mode === m ? "gradient-btn text-white" : "glass-card text-gray-600"}`}>
                {m === "manual" ? "Book manually" : "AI Booking"}
              </button>
            ))}
          </div>
          {mode === "manual" ? <BookingStep token={token} /> : <AIBookingStep token={token} />}
        </>
      )}
    </div>
  );
}
