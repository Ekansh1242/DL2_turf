import { GraduationCap, LogOut, ShieldCheck } from "lucide-react";

export default function TopNav({
  role,
  onLogout,
}: {
  role: string;
  onLogout: () => void;
}) {
  return (
    <div className="sticky top-0 z-20 backdrop-blur-md bg-white/70 border-b border-gray-100">
      <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg gradient-btn flex items-center justify-center text-white">
            <GraduationCap size={14} />
          </div>
          <span className="text-sm font-extrabold gradient-text">CampusSphere AI</span>
          {role === "admin" && (
            <span className="badge bg-violet-50 text-violet-600 ml-1">
              <ShieldCheck size={11} /> Staff
            </span>
          )}
        </div>
        <button
          onClick={onLogout}
          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-red-500 transition-colors"
        >
          <LogOut size={13} /> Log out
        </button>
      </div>
    </div>
  );
}
