import React, { useEffect, useState } from 'react';
import Auth from './Auth';
import Dashboard from './Dashboard';
import Landing from './Landing';
import { auth, onAuthStateChanged, signOut } from './firebase';

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showAuth, setShowAuth] = useState(false);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      setLoading(false);
    });
    return () => unsubscribe();
  }, []);

  const handleLogout = async () => {
    await signOut(auth);
    setShowAuth(false);
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0B1B3D] text-white">
        <p className="text-lg font-bold tracking-[0.28em] text-[#BBD987] animate-pulse">
          INITIALIZING AGRA CORE...
        </p>
      </div>
    );
  }

  // logged in — show dashboard
  if (user) {
    return <Dashboard user={user} onLogout={handleLogout} />;
  }

  // not logged in, showing auth screen
  if (showAuth) {
    return (
      <Auth
        onLoginSuccess={() => setShowAuth(false)}
        onBack={() => setShowAuth(false)}
      />
    );
  }

  // default — landing page
  return <Landing onLoginClick={() => setShowAuth(true)} />;
}