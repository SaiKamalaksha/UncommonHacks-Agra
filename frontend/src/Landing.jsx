import React from 'react';

const EXE_URL = "https://github.com/SaiKamalaksha/UncommonHacks-Agra/releases/download/v1.0.0/AgraSecurity.exe";

export default function Landing({ onLoginClick }) {
  return (
    <div className="min-h-screen bg-[#0B1B3D] text-white flex flex-col">

      {/* navbar */}
      <nav className="flex items-center justify-between px-8 py-5 border-b border-white/10">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.34em] text-[#BBD987]">AGRA</p>
          <p className="text-xs text-slate-400 tracking-widest">SECURITY</p>
        </div>
        <button
          onClick={onLoginClick}
          className="rounded-lg border border-[#BBD987]/40 px-5 py-2 text-sm font-bold text-[#BBD987] hover:bg-[#BBD987]/10 transition"
        >
          Sign In
        </button>
      </nav>

      {/* hero */}
      <main className="flex flex-1 flex-col items-center justify-center px-4 text-center gap-8">
        <div className="flex flex-col items-center gap-4">
          <div className="rounded-full border border-[#BBD987]/30 bg-[#BBD987]/10 px-4 py-1.5 text-xs font-bold uppercase tracking-[0.3em] text-[#BBD987]">
            NPU-Powered Endpoint Security
          </div>
          <h1 className="text-5xl font-black tracking-tight text-white sm:text-6xl lg:text-7xl">
            Stop Threats.<br />
            <span className="text-[#BBD987]">Before They Start.</span>
          </h1>
          <p className="max-w-xl text-lg text-slate-300 leading-relaxed">
            Agra runs silently in the background, using your laptop's onboard AI chip to detect and delete malicious files the moment they land — no cloud round trips, no CPU tax.
          </p>
        </div>

        {/* download button */}
        <div className="flex flex-col items-center gap-3">
          <a
            href={EXE_URL}
            download
            className="flex items-center gap-3 rounded-xl bg-[#BBD987] px-8 py-4 text-lg font-black text-[#0B1B3D] hover:bg-[#a6c476] transition shadow-lg shadow-[#BBD987]/20"
          >
            <span>⬇</span>
            Download Agra for Windows
          </a>
          <p className="text-xs text-slate-500">Windows 10/11 · Intel NPU supported · Free during beta</p>
        </div>

        {/* stats bar */}
        <div className="grid grid-cols-3 gap-6 rounded-xl border border-white/10 bg-[#2F3E46]/40 px-10 py-6 text-center">
          <div>
            <p className="text-3xl font-black text-[#BBD987]">0ms</p>
            <p className="text-xs text-slate-400 mt-1">Cloud Latency</p>
          </div>
          <div>
            <p className="text-3xl font-black text-[#BBD987]">NPU</p>
            <p className="text-xs text-slate-400 mt-1">On-Device Inference</p>
          </div>
          <div>
            <p className="text-3xl font-black text-[#BBD987]">24/7</p>
            <p className="text-xs text-slate-400 mt-1">Always-On Protection</p>
          </div>
        </div>

        {/* how it works */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 max-w-3xl w-full">
          {[
            { step: "01", title: "Download & Install", desc: "One click install. No configuration needed. Runs silently in your system tray." },
            { step: "02", title: "Real-Time Detection", desc: "Every file in your Downloads and Desktop is scored instantly using our ML model on your NPU." },
            { step: "03", title: "Live Dashboard", desc: "Sign in to see every threat stopped, file scanned, and alert generated across your devices." },
          ].map(({ step, title, desc }) => (
            <div key={step} className="rounded-xl border border-white/10 bg-[#2F3E46]/40 p-5 text-left">
              <p className="text-xs font-black text-[#BBD987] tracking-widest">{step}</p>
              <p className="mt-2 font-bold text-white">{title}</p>
              <p className="mt-1 text-sm text-slate-400">{desc}</p>
            </div>
          ))}
        </div>

        <button
          onClick={onLoginClick}
          className="text-sm text-slate-400 hover:text-[#BBD987] transition underline underline-offset-4"
        >
          Already have an account? View your dashboard →
        </button>
      </main>

      {/* footer */}
      <footer className="border-t border-white/10 px-8 py-4 text-center text-xs text-slate-500">
        © 2026 Agra Security · Built at Uncommon Hacks
      </footer>
    </div>
  );
}