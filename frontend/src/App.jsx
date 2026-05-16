// src/App.jsx
import React, { useState, useEffect } from 'react';
import { auth, onAuthStateChanged, signOut } from './firebase';
import Auth from './Auth';
// import Dashboard from './components/Dashboard'; // Your dashboard component

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Listen for session changes (login / logout)
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      setLoading(false);
    });

    return () => unsubscribe(); // Cleanup listener on unmount
  }, []);

  const handleLogout = async () => {
    await signOut(auth);
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0B1B3D] text-white">
        <p className="text-lg tracking-widest animate-pulse">INITIALIZING AGRA CORE...</p>
      </div>
    );
  }

  // If user is not logged in, show the Auth screen
  if (!user) {
    return <Auth onLoginSuccess={() => {}} />;
  }

  // If logged in, show your main dashboard layout
  return (
    <div className="min-h-screen bg-[#0B1B3D] text-white">
      {/* Quick Temporary Header with Logout */}
      <nav className="flex justify-between items-center p-4 bg-[#2F3E46]/30 border-b border-slate-700">
        <span className="font-bold tracking-wider text-[#BBD987]">AGRA SECURE TRACE</span>
        <button 
          onClick={handleLogout}
          className="px-3 py-1 text-xs rounded border border-red-400 text-red-400 hover:bg-red-500/10 transition-colors"
        >
          Disconnect Agent
        </button>
      </nav>

      {/* Put your Dashboard Grid Component here */}
      <div className="p-6">
        <h1 className="text-2xl font-bold">Welcome to the Cockpit, {user.email}</h1>
        <p className="text-slate-400 mt-2">Replace this space with your Donut charts, settings sliders, and Nisitha's alert stream feed.</p>
      </div>
    </div>
  );
}
