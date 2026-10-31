import { useEffect, useState } from 'react';
import { requestLoginOTP, verifyLoginOTP } from '../api/client';

export default function LoginStep({ onLoggedIn }: { onLoggedIn: (token: string, role: string) => void }) {
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [roll, setRoll] = useState('');
  const [department, setDepartment] = useState('');
  const [code, setCode] = useState('');
  const [stage, setStage] = useState<'email'|'code'>('email');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [wait, setWait] = useState(0);
  useEffect(() => {
    if (!wait) return;
    const timer = window.setTimeout(() => setWait(wait - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [wait]);
  async function send() {
    setBusy(true); setError(''); setMessage('');
    try {
      const result = await requestLoginOTP(email.trim());
      setStage('code'); setCode(''); setWait(result.resend_after); setMessage(result.message);
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not send code.'); }
    finally { setBusy(false); }
  }
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (stage === 'email') { await send(); return; }
    setBusy(true); setError('');
    try {
      const result = await verifyLoginOTP(email.trim(), code, name.trim(), roll.trim(), department.trim());
      onLoggedIn(result.access_token, result.role);
    } catch (err) { setError(err instanceof Error ? err.message : 'Verification failed.'); }
    finally { setBusy(false); }
  }
  return <main className="min-h-screen flex items-center justify-center px-4 py-10">
    <section className="glass-card rounded-2xl p-8 w-full max-w-md">
      <h1 className="text-2xl font-bold gradient-text">CampusSphere</h1>
      <h2 className="text-lg font-semibold mt-4">Sign in with an email code</h2>
      <p className="text-sm text-gray-500 mt-2 mb-5">Use your college email or your configured staff email. No password required.</p>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <label className="text-sm">Email address<input className="input-field mt-1" type="email" autoComplete="email" required value={email} disabled={stage === 'code' || busy} onChange={e=>setEmail(e.target.value)} /></label>
        {stage === 'code' && <>
          <label className="text-sm">Your name<input className="input-field mt-1" required maxLength={100} autoComplete="name" value={name} onChange={e=>setName(e.target.value)} /></label>
          <label className="text-sm">Roll number (optional for staff)<input className="input-field mt-1" maxLength={80} value={roll} onChange={e=>setRoll(e.target.value)} /></label>
          <label className="text-sm">Department (optional)<input className="input-field mt-1" maxLength={100} value={department} onChange={e=>setDepartment(e.target.value)} /></label>
          <label className="text-sm">Six-digit code<input className="input-field mt-1" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" required maxLength={6} value={code} onChange={e=>setCode(e.target.value.replace(/\D/g,''))} /></label>
          <p className="text-xs text-gray-500">The code expires after five minutes. Only the latest code works.</p>
        </>}
        <button className="gradient-btn text-white rounded-xl py-3" disabled={busy}>{busy ? 'Please wait…' : stage === 'email' ? 'Send sign-in code' : 'Verify and sign in'}</button>
        {stage === 'code' && <div className="flex justify-between text-sm">
          <button type="button" className="text-violet-700" disabled={busy || wait > 0} onClick={send}>{wait ? `Resend in ${wait}s` : 'Resend code'}</button>
          <button type="button" disabled={busy} onClick={()=>{setStage('email');setCode('');setError('');setMessage('');}}>Change email</button>
        </div>}
      </form>
      {message && <p role="status" className="text-sm text-green-700 mt-3">{message}</p>}
      {error && <p role="alert" className="text-sm text-red-600 mt-3">{error}</p>}
    </section>
  </main>;
}
