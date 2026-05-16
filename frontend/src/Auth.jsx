// src/Auth.jsx
import React, { useState } from 'react';
import {
  auth,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  updateProfile,
} from './firebase';

export default function Auth({ onLoginSuccess }) {
  const [isRegistering, setIsRegistering] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isRegistering) {
        const credential = await createUserWithEmailAndPassword(auth, email, password);
        await updateProfile(credential.user, {
          displayName: name.trim(),
        });
      } else {
        await signInWithEmailAndPassword(auth, email, password);
      }
      onLoginSuccess();
    } catch (err) {
      setError(err.message.replace('Firebase: ', ''));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0B1B3D] px-4">
      <div className="w-full max-w-md space-y-8 rounded-xl bg-[#2F3E46]/40 p-8 shadow-2xl backdrop-blur-md border border-slate-700">
        <div className="text-center">
          <h2 className="text-4xl font-extrabold tracking-wider text-white">AGRA</h2>
          <p className="mt-2 text-sm text-slate-300">
            {isRegistering ? 'Create your security account' : 'Sign in to your security terminal'}
          </p>
        </div>

        {error && (
          <div className="rounded-md bg-red-500/10 border border-red-500/30 p-3 text-sm text-red-400 text-center">
            {error}
          </div>
        )}

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="space-y-4 rounded-md shadow-sm">
            {isRegistering && (
              <div>
                <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Name</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="mt-1 w-full rounded-lg bg-[#0B1B3D] border border-slate-600 px-4 py-3 text-white placeholder-slate-500 focus:border-[#BBD987] focus:outline-none transition-colors"
                  placeholder="Name"
                />
              </div>
            )}
            <div>
              <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Email Address</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full rounded-lg bg-[#0B1B3D] border border-slate-600 px-4 py-3 text-white placeholder-slate-500 focus:border-[#BBD987] focus:outline-none transition-colors"
                placeholder="name@email.com"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full rounded-lg bg-[#0B1B3D] border border-slate-600 px-4 py-3 text-white placeholder-slate-500 focus:border-[#BBD987] focus:outline-none transition-colors"
                placeholder="Password"
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={loading}
              className="group relative flex w-full justify-center rounded-lg bg-[#BBD987] px-4 py-3 text-sm font-bold text-[#0B1B3D] hover:bg-[#a6c476] focus:outline-none transition-colors disabled:opacity-50"
            >
              {loading ? 'Processing...' : isRegistering ? 'Register Agent' : 'Authenticate'}
            </button>
          </div>
        </form>

        <div className="text-center text-sm">
          <button
            onClick={() => {
              setIsRegistering(!isRegistering);
              setError('');
              setName('');
            }}
            className="font-medium text-[#BBD987] hover:underline focus:outline-none"
          >
            {isRegistering ? 'Already have an account? Sign In' : "Don't have an account? Register"}
          </button>
        </div>
      </div>
    </div>
  );
}
