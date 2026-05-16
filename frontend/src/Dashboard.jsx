import React, { useEffect, useMemo, useState } from 'react';

const initialAlerts = [
  { id: 1, timestamp: '14:02:11', filename: 'notepad.exe', score: 8 },
  { id: 2, timestamp: '14:03:27', filename: 'unknown_patch.exe', score: 58 },
  { id: 3, timestamp: '14:04:43', filename: 'mimikatz.exe', score: 96 },
  { id: 4, timestamp: '14:06:05', filename: 'invoice_macro.xlsm', score: 74 },
];

const simulatedEvents = [
  { filename: 'kernel_update.tmp', score: 24 },
  { filename: 'browser_cache.bin', score: 12 },
  { filename: 'credential_dump.ps1', score: 91 },
  { filename: 'signed_driver.sys', score: 33 },
  { filename: 'remote_payload.dll', score: 82 },
  { filename: 'unknown_patch.exe', score: 61 },
];

function getVerdict(score) {
  if (score > 70) return 'Malicious';
  if (score >= 40) return 'Suspicious';
  return 'Benign';
}

function getAlertStyles(score) {
  const verdict = getVerdict(score);

  if (verdict === 'Malicious') {
    return {
      row: 'border-red-500/20 bg-red-500/10 text-red-100',
      badge: 'border-red-500/30 bg-red-500/15 text-red-400',
      score: 'text-red-400',
    };
  }

  if (verdict === 'Suspicious') {
    return {
      row: 'border-amber-500/20 bg-amber-500/10 text-amber-100',
      badge: 'border-amber-500/30 bg-amber-500/15 text-amber-300',
      score: 'text-amber-300',
    };
  }

  return {
    row: 'border-[#BBD987]/20 bg-[#BBD987]/10 text-lime-50',
    badge: 'border-[#BBD987]/30 bg-[#BBD987]/15 text-[#BBD987]',
    score: 'text-[#BBD987]',
  };
}

function Toggle({ label, enabled, onChange }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!enabled)}
      className="flex w-full items-center justify-between gap-4 rounded-lg border border-white/10 bg-[#0B1B3D]/60 px-4 py-3 text-left transition hover:border-[#BBD987]/40"
    >
      <span className="text-sm font-medium text-slate-100">{label}</span>
      <span
        className={`flex h-6 w-11 items-center rounded-full border p-1 transition ${
          enabled ? 'border-[#BBD987]/60 bg-[#BBD987]/25' : 'border-slate-600 bg-slate-700/50'
        }`}
      >
        <span
          className={`h-4 w-4 rounded-full transition ${
            enabled ? 'translate-x-5 bg-[#BBD987]' : 'translate-x-0 bg-slate-300'
          }`}
        />
      </span>
    </button>
  );
}

export default function Dashboard({ user, onLogout }) {
  const [alerts, setAlerts] = useState(initialAlerts);
  const [threshold, setThreshold] = useState(70);
  const [realTimeMonitoring, setRealTimeMonitoring] = useState(true);
  const [npuAcceleration, setNpuAcceleration] = useState(true);

  useEffect(() => {
    const pollAlerts = setInterval(() => {
      /*
        Replace this mock updater with your live backend later:

        const response = await fetch('YOUR_NGROK_URL/alerts');
        const liveAlerts = await response.json();
        setAlerts(liveAlerts);
      */
      setAlerts((currentAlerts) => {
        const event = simulatedEvents[Math.floor(Math.random() * simulatedEvents.length)];
        const nextAlert = {
          id: Date.now(),
          timestamp: new Date().toLocaleTimeString([], {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
          }),
          filename: event.filename,
          score: event.score,
        };

        return [nextAlert, ...currentAlerts].slice(0, 8);
      });
    }, 3000);

    return () => clearInterval(pollAlerts);
  }, []);

  const metrics = useMemo(() => {
    const threats = alerts.filter((alert) => alert.score > 70).length;
    const warnings = alerts.filter((alert) => alert.score >= 40 && alert.score <= 70).length;
    const safe = alerts.filter((alert) => alert.score < 40).length;

    return {
      scanned: 12847 + alerts.length,
      threats,
      warnings,
      safe,
    };
  }, [alerts]);

  const totalChart = Math.max(metrics.threats + metrics.warnings + metrics.safe, 1);
  const threatPercent = (metrics.threats / totalChart) * 100;
  const warningPercent = (metrics.warnings / totalChart) * 100;
  const displayName = user?.displayName || user?.email?.split('@')[0] || 'Agent';

  return (
    <main className="min-h-screen bg-[#0B1B3D] px-4 py-5 text-white sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-5">
        <header className="flex flex-col gap-4 rounded-lg border border-white/10 bg-[#2F3E46]/40 px-5 py-4 shadow-2xl shadow-black/20 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.34em] text-[#BBD987]">AGRA</p>
            <h1 className="mt-2 text-2xl font-black tracking-wide text-white sm:text-3xl">Threat Intelligence Dashboard</h1>
            <p className="mt-2 text-sm font-medium text-slate-300">Welcome, {displayName}</p>
          </div>

          <div className="flex flex-col gap-3 sm:items-end">
            <div className="inline-flex w-fit items-center gap-3 rounded-full border border-[#BBD987]/30 bg-[#BBD987]/10 px-4 py-2 text-sm font-semibold text-[#BBD987]">
              <span className="relative flex h-3 w-3">
                <span className="absolute inline-flex h-full w-full animate-pulse rounded-full bg-[#BBD987] opacity-75" />
                <span className="relative inline-flex h-3 w-3 rounded-full bg-[#BBD987]" />
              </span>
              Agent State: Active on NPU
            </div>
            {onLogout && (
              <button
                type="button"
                onClick={onLogout}
                className="w-fit rounded-lg border border-red-400/40 px-3 py-2 text-xs font-bold uppercase tracking-[0.18em] text-red-300 transition hover:bg-red-500/10"
              >
                Log Out
              </button>
            )}
          </div>
        </header>

        <section className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-lg border border-white/10 bg-[#2F3E46]/40 p-5 shadow-2xl shadow-black/20">
            <div className="flex flex-col gap-6 md:flex-row md:items-center">
              <div className="flex flex-1 items-center justify-center">
                <div className="relative h-64 w-64">
                  <svg className="h-full w-full -rotate-90" viewBox="0 0 120 120" aria-label="Threat breakdown donut chart">
                    <circle cx="60" cy="60" r="42" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="18" />
                    <circle
                      cx="60"
                      cy="60"
                      r="42"
                      fill="none"
                      stroke="#ef4444"
                      strokeWidth="18"
                      strokeDasharray={`${threatPercent} ${100 - threatPercent}`}
                      pathLength="100"
                    />
                    <circle
                      cx="60"
                      cy="60"
                      r="42"
                      fill="none"
                      stroke="#f59e0b"
                      strokeWidth="18"
                      strokeDasharray={`${warningPercent} ${100 - warningPercent}`}
                      strokeDashoffset={-threatPercent}
                      pathLength="100"
                    />
                    <circle
                      cx="60"
                      cy="60"
                      r="42"
                      fill="none"
                      stroke="#BBD987"
                      strokeWidth="18"
                      strokeDasharray={`${100 - threatPercent - warningPercent} ${threatPercent + warningPercent}`}
                      strokeDashoffset={-(threatPercent + warningPercent)}
                      pathLength="100"
                    />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-4xl font-black text-white">{totalChart}</span>
                    <span className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-300">Detections</span>
                  </div>
                </div>
              </div>

              <div className="grid flex-1 gap-3">
                <div className="flex items-center justify-between rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3">
                  <span className="text-sm text-red-100">Stopped Threats</span>
                  <span className="text-2xl font-black text-red-400">{metrics.threats}</span>
                </div>
                <div className="flex items-center justify-between rounded-lg border border-amber-500/20 bg-amber-500/10 px-4 py-3">
                  <span className="text-sm text-amber-100">Warnings</span>
                  <span className="text-2xl font-black text-amber-300">{metrics.warnings}</span>
                </div>
                <div className="flex items-center justify-between rounded-lg border border-[#BBD987]/20 bg-[#BBD987]/10 px-4 py-3">
                  <span className="text-sm text-lime-50">Safe Files</span>
                  <span className="text-2xl font-black text-[#BBD987]">{metrics.safe}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="grid gap-4 rounded-lg border border-white/10 bg-[#2F3E46]/40 p-5 shadow-2xl shadow-black/20">
            <div className="rounded-lg border border-white/10 bg-[#0B1B3D]/60 p-5">
              <p className="text-sm font-semibold uppercase tracking-[0.22em] text-slate-400">Total Files Scanned</p>
              <p className="mt-3 text-5xl font-black tracking-wide text-white">{metrics.scanned.toLocaleString()}</p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-5">
                <p className="text-sm font-semibold text-red-100">Total Threats Detected</p>
                <p className="mt-3 text-4xl font-black text-red-400">{metrics.threats}</p>
              </div>
              <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-5">
                <p className="text-sm font-semibold text-amber-100">Total Warnings</p>
                <p className="mt-3 text-4xl font-black text-amber-300">{metrics.warnings}</p>
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-5 lg:grid-cols-[0.85fr_1.15fr]">
          <div className="rounded-lg border border-white/10 bg-[#2F3E46]/40 p-5 shadow-2xl shadow-black/20">
            <div className="flex items-center justify-between gap-4">
              <h2 className="text-lg font-bold tracking-wide text-white">Antivirus Settings</h2>
              <span className="rounded-full border border-[#BBD987]/20 bg-[#BBD987]/10 px-3 py-1 text-xs font-bold text-[#BBD987]">
                Guarded
              </span>
            </div>

            <div className="mt-6 rounded-lg border border-white/10 bg-[#0B1B3D]/60 p-4">
              <div className="flex items-center justify-between gap-4">
                <label htmlFor="threshold" className="text-sm font-medium text-slate-100">
                  Threat Score Threshold
                </label>
                <span className="text-lg font-black text-[#BBD987]">{threshold}%</span>
              </div>
              <input
                id="threshold"
                type="range"
                min="1"
                max="100"
                value={threshold}
                onChange={(event) => setThreshold(Number(event.target.value))}
                className="mt-4 h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-700 accent-[#BBD987]"
              />
              <div className="mt-2 flex justify-between text-xs text-slate-400">
                <span>Lenient</span>
                <span>Aggressive</span>
              </div>
            </div>

            <div className="mt-4 grid gap-3">
              <Toggle label="Real-time Monitoring" enabled={realTimeMonitoring} onChange={setRealTimeMonitoring} />
              <Toggle label="Local NPU Acceleration" enabled={npuAcceleration} onChange={setNpuAcceleration} />
            </div>
          </div>

          <div className="rounded-lg border border-white/10 bg-[#2F3E46]/40 p-5 shadow-2xl shadow-black/20">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="text-lg font-bold tracking-wide text-white">Live Alert Feed</h2>
              <span className="font-mono text-xs uppercase tracking-[0.2em] text-slate-400">Polling: 3s</span>
            </div>

            <div className="mt-5 max-h-[23rem] overflow-y-auto rounded-lg border border-white/10 bg-black/30 p-3 font-mono text-sm">
              <div className="grid min-w-[38rem] gap-3">
                {alerts.map((alert) => {
                  const styles = getAlertStyles(alert.score);
                  const verdict = getVerdict(alert.score);

                  return (
                    <div
                      key={alert.id}
                      className={`grid grid-cols-[5.5rem_1fr_7rem_4rem] items-center gap-3 rounded-lg border px-3 py-3 ${styles.row}`}
                    >
                      <span className="text-slate-300">{alert.timestamp}</span>
                      <span className="truncate font-semibold text-white">{alert.filename}</span>
                      <span className={`rounded-full border px-2 py-1 text-center text-xs font-black uppercase ${styles.badge}`}>
                        {verdict}
                      </span>
                      <span className={`text-right font-black ${styles.score}`}>{alert.score}%</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
