const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export interface LoginResult {
  access_token: string;
  role: string;
  user_id: string;
}

export interface TraceStep {
  node: string;
  status: string; // completed | fallback | failed
  summary: string;
  duration_ms: number;
  tool?: string;
}

export interface AICandidate {
  candidate_id: string;
  start: string;
  end: string;
  bookable_now: boolean;
  opens_at: string;
  usable_minutes: number;
  minutes_from_preferred: number;
  turf_load_today: number;
  back_to_back: boolean;
}

export interface AIBookResult {
  email_sent: boolean;
  // confirmed | needs_confirmation | recommendation | needs_info | rejected | not_yet_open | escalated
  status: string;
  booking_id: string | null;
  resource_name: string | null;
  message: string;
  proposal: { resource_id: string; slot_start: string; slot_end: string } | null;
  candidates: AICandidate[];
  decision_source: string | null;
  total_ms: number;
  trace: TraceStep[];
}

export interface AnalyticsAnswer {
  answer: string;
  tool: string;
  data: unknown;
  trace: TraceStep[];
}

export interface Sport {
  sport: string;
  resource_id: string;
  resource_name: string;
}

export interface Slot {
  slot_start: string;
  slot_end: string;
  window_opens_at: string;
  is_booked: boolean;
  is_bookable_now: boolean;
}

export interface ConfirmBookingResult {
  success: boolean;
  booking_id: string | null;
  message: string;
  next_window_opens_at: string | null;
  email_sent: boolean;
}

export interface MyBooking {
  id: string;
  resource_name: string;
  sport: string;
  start_time: string;
  end_time: string;
  status: string;
  cancel_deadline: string;
  can_cancel: boolean;
}

export interface CancelResult {
  success: boolean;
  message: string;
}

export interface JoinWaitlistResult {
  success: boolean;
  entry_id: string | null;
  message: string;
}

export interface SummaryOut {
  total_bookings: number;
  confirmed_bookings: number;
  cancelled_bookings: number;
  no_shows: number;
  unique_students: number;
  total_fines_rupees: number;
  bookings_this_week: number;
}

export interface TrendPoint { date: string; count: number }
export interface SportBreakdown { sport: string; count: number }
export interface DeptBreakdown { department: string; count: number }
export interface YearBreakdown { year: number; count: number }
export interface PeakHour { hour: number; count: number }
export interface TopStudent { name: string; email: string; booking_count: number }

export interface StudentOut {
  id: string;
  name: string;
  email: string;
  roll_no: string | null;
  department: string | null;
  is_blocked: boolean;
}

export interface BookForResult {
  success: boolean;
  booking_id: string | null;
  message: string;
  email_sent: boolean;
}

export interface EquipmentIssueBreakdown { equipment_name: string; damaged_count: number; lost_count: number; total_fines_rupees: number }
export interface StudentFine { name: string; email: string; total_fines_rupees: number }
export interface TodayBooking {
  booking_id: string;
  student_name: string;
  resource_name: string;
  start_time: string;
  end_time: string;
  status: string;
  checked_in: boolean;
}

async function req<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `Request failed: ${res.status}`);
  return data as T;
}

export function login(email: string, name: string, rollNo: string, department?: string) {
  return req<LoginResult>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, name, roll_no: rollNo, department }),
  });
}

export function aiBook(message: string, token: string) {
  return req<AIBookResult>(
    "/api/v1/bookings/ai-book",
    { method: "POST", body: JSON.stringify({ message }) },
    token
  );
}

export function listSports(token: string) {
  return req<Sport[]>("/api/v1/sports", {}, token);
}

export function listSlots(resourceId: string, date: string, token: string) {
  return req<Slot[]>(
    `/api/v1/slots?resource_id=${encodeURIComponent(resourceId)}&date=${encodeURIComponent(date)}`,
    {},
    token
  );
}

export function confirmBooking(resourceId: string, slotStart: string, slotEnd: string, token: string) {
  return req<ConfirmBookingResult>(
    "/api/v1/bookings/confirm",
    { method: "POST", body: JSON.stringify({ resource_id: resourceId, slot_start: slotStart, slot_end: slotEnd }) },
    token
  );
}

export async function downloadReceipt(bookingId: string, token: string) {
  const res = await fetch(`${API_BASE}/api/v1/bookings/${bookingId}/receipt.pdf`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Failed to fetch receipt: ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `campussphere-receipt-${bookingId.slice(0, 8)}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// ---------- Admin ----------

export function adminSummary(token: string) {
  return req<SummaryOut>("/api/v1/admin/analytics/summary", {}, token);
}

export function adminTrend(token: string, days = 30) {
  return req<TrendPoint[]>(`/api/v1/admin/analytics/trend?days=${days}`, {}, token);
}

export function adminBySport(token: string) {
  return req<SportBreakdown[]>("/api/v1/admin/analytics/by-sport", {}, token);
}

export function adminByDepartment(token: string) {
  return req<DeptBreakdown[]>("/api/v1/admin/analytics/by-department", {}, token);
}

export function adminByYear(token: string) {
  return req<YearBreakdown[]>("/api/v1/admin/analytics/by-year", {}, token);
}

export function adminPeakHours(token: string) {
  return req<PeakHour[]>("/api/v1/admin/analytics/peak-hours", {}, token);
}

export function adminTopStudents(token: string) {
  return req<TopStudent[]>("/api/v1/admin/analytics/top-students", {}, token);
}

export function adminSearchStudents(q: string, token: string) {
  return req<StudentOut[]>(`/api/v1/admin/students/search?q=${encodeURIComponent(q)}`, {}, token);
}

export function adminBookFor(studentId: string, resourceId: string, slotStart: string, slotEnd: string, token: string) {
  return req<BookForResult>(
    "/api/v1/admin/bookings/book-for",
    { method: "POST", body: JSON.stringify({ student_id: studentId, resource_id: resourceId, slot_start: slotStart, slot_end: slotEnd }) },
    token
  );
}

async function downloadBlob(path: string, filename: string, token: string) {
  const res = await fetch(`${API_BASE}${path}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error(`Failed to download: ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function downloadBookingsCsv(token: string) {
  return downloadBlob("/api/v1/admin/reports/bookings.csv", "campussphere-bookings.csv", token);
}

export function downloadSummaryPdf(token: string) {
  return downloadBlob("/api/v1/admin/reports/summary.pdf", "campussphere-summary-report.pdf", token);
}

// ---------- My bookings / cancel / waitlist ----------

export function myBookings(token: string) {
  return req<MyBooking[]>("/api/v1/bookings/mine", {}, token);
}

export function cancelBooking(bookingId: string, token: string) {
  return req<CancelResult>(`/api/v1/bookings/${bookingId}/cancel`, { method: "PATCH" }, token);
}

export function joinWaitlist(resourceId: string, slotStart: string, slotEnd: string, token: string) {
  return req<JoinWaitlistResult>(
    "/api/v1/bookings/waitlist/join",
    { method: "POST", body: JSON.stringify({ resource_id: resourceId, slot_start: slotStart, slot_end: slotEnd }) },
    token
  );
}

// ---------- Admin: equipment analytics, today's bookings, check-in/no-show ----------

export function adminEquipmentIssues(token: string) {
  return req<EquipmentIssueBreakdown[]>("/api/v1/admin/analytics/equipment-issues", {}, token);
}

export function adminFinesByStudent(token: string) {
  return req<StudentFine[]>("/api/v1/admin/analytics/fines-by-student", {}, token);
}

export function adminTodaysBookings(token: string) {
  return req<TodayBooking[]>("/api/v1/admin/bookings/today", {}, token);
}

export function adminCheckIn(bookingId: string, token: string) {
  return req<{ success: boolean; student_name: string | null; resource_name: string | null; message: string }>(
    `/api/v1/admin/bookings/${bookingId}/check-in`, { method: "POST" }, token
  );
}

export function adminMarkNoShow(bookingId: string, token: string) {
  return req<{ success: boolean; message: string }>(
    `/api/v1/admin/bookings/${bookingId}/no-show`, { method: "POST" }, token
  );
}

export function askAnalytics(question: string, token: string) {
  return req<AnalyticsAnswer>(
    "/api/v1/admin/analytics/ask",
    { method: "POST", body: JSON.stringify({ question }) },
    token
  );
}
