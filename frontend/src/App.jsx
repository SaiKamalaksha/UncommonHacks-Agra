import React, { useEffect, useState } from 'react';
import Auth from './Auth';
import Dashboard from './Dashboard';
import { auth, onAuthStateChanged, signOut } from './firebase';

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  const handleLogout = async () => {
    await signOut(auth);
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0B1B3D] text-white">
        <p className="text-lg font-bold tracking-[0.28em] text-[#BBD987] animate-pulse">INITIALIZING AGRA CORE...</p>
      </div>
    );
  }

  if (!user) {
    return <Auth onLoginSuccess={() => {}} />;
  }

  return <Dashboard user={user} onLogout={handleLogout} />;
}
