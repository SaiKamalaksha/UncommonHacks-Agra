// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
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
const analytics = getAnalytics(app);