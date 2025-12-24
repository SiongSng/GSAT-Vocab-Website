import { initializeApp } from "firebase/app";
import {
  getAuth,
  GoogleAuthProvider,
  browserLocalPersistence,
  setPersistence,
} from "firebase/auth";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey: "AIzaSyA3vmSo8OGAQAWfyvgCLx811bJjq2PU89I",
  authDomain: "gsat-vocab-website.firebaseapp.com",
  projectId: "gsat-vocab-website",
  storageBucket: "gsat-vocab-website.firebasestorage.app",
  messagingSenderId: "752021009254",
  appId: "1:752021009254:web:ad102469461238ac178ea7",
  measurementId: "G-KNG0LBFEWP",
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
export const googleProvider = new GoogleAuthProvider();

export const authReady = setPersistence(auth, browserLocalPersistence).catch(
  () => undefined,
);
