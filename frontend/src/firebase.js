import { initializeApp } from "firebase/app";
import {
  createUserWithEmailAndPassword,
  getAuth,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut,
} from "firebase/auth";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyBJ8mHY6xGVfvwF3za8KU6Ev4BeCh4tS7c",
  authDomain: "agra-21e39.firebaseapp.com",
  projectId: "agra-21e39",
  storageBucket: "agra-21e39.firebasestorage.app",
  messagingSenderId: "334831660644",
  appId: "1:334831660644:web:8056b0779bbefc1beff971",
  measurementId: "G-EQ7LB042B2"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

export {
  auth,
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut,
};
