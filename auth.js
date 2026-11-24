/* Maternacare AI — authentication (Firebase Auth with local demo fallback).
 * Firebase config lives in firebase-config.js. When unconfigured, a local
 * demo mode stores accounts in this browser only (NOT secure, for testing).
 */

const AUTH_KEY = 'mc_auth_user';
const LOCAL_USERS_KEY = 'mc_local_users';

function config() {
  return (typeof window !== 'undefined' && window.FIREBASE_CONFIG) || (typeof FIREBASE_CONFIG !== 'undefined' ? FIREBASE_CONFIG : {});
}
function firebaseConfigured() {
  const c = config();
  return c.apiKey && !c.apiKey.startsWith('PLACEHOLDER');
}

function currentUser() {
  try { return JSON.parse(localStorage.getItem(AUTH_KEY) || 'null'); } catch (_) { return null; }
}

function saveLocalUser(u) { localStorage.setItem(AUTH_KEY, JSON.stringify(u)); }
function clearLocalUser() { localStorage.removeItem(AUTH_KEY); }

function authId() {
  const u = currentUser();
  return u ? u.uid : Payments.getDeviceId();
}

/* ---- Firebase SDK (loaded dynamically only when configured) ---- */
let fbAuth = null;
async function initFirebase() {
  if (!firebaseConfigured() || typeof firebase === 'undefined') return false;
  try {
    if (!firebase.apps.length) firebase.initializeApp(config());
    fbAuth = firebase.auth();
    return true;
  } catch (_) { return false; }
}

/* Email/password sign-up */
async function signUpEmail(email, password) {
  if (firebaseConfigured() && fbAuth) {
    const cred = await fbAuth.createUserWithEmailAndPassword(email, password);
    const u = { uid: cred.user.uid, email: cred.user.email, provider: 'email' };
    saveLocalUser(u); return u;
  }
  // Local demo fallback
  const users = JSON.parse(localStorage.getItem(LOCAL_USERS_KEY) || '[]');
  if (users.some(x => x.email === email)) throw new Error('Account already exists');
  const u = { uid: 'local_' + Date.now(), email, provider: 'email-demo' };
  users.push({ email, password });
  localStorage.setItem(LOCAL_USERS_KEY, JSON.stringify(users));
  saveLocalUser(u); return u;
}

async function signInEmail(email, password) {
  if (firebaseConfigured() && fbAuth) {
    const cred = await fbAuth.signInWithEmailAndPassword(email, password);
    const u = { uid: cred.user.uid, email: cred.user.email, provider: 'email' };
    saveLocalUser(u); return u;
  }
  const users = JSON.parse(localStorage.getItem(LOCAL_USERS_KEY) || '[]');
  const found = users.find(x => x.email === email && x.password === password);
  if (!found) throw new Error('Wrong email or password');
  const u = { uid: 'local_' + email, email, provider: 'email-demo' };
  saveLocalUser(u); return u;
}

/* Phone: send OTP (Firebase only). Returns a confirmation result. */
async function sendPhoneOtp(phone, recaptchaContainer) {
  if (!firebaseConfigured() || !fbAuth) throw new Error('Phone login needs Firebase configured');
  const verifier = new firebase.auth.RecaptchaVerifier(recaptchaContainer, { size: 'invisible' });
  return await fbAuth.signInWithPhoneNumber(phone, verifier);
}

async function confirmPhoneOtp(confirmationResult, code) {
  const cred = await confirmationResult.confirm(code);
  const u = { uid: cred.user.uid, phone: cred.user.phoneNumber, provider: 'phone' };
  saveLocalUser(u); return u;
}

async function signOut() {
  if (firebaseConfigured() && fbAuth) await fbAuth.signOut();
  clearLocalUser();
}

function watchAuth(callback) {
  if (firebaseConfigured() && fbAuth) fbAuth.onAuthStateChanged(user => {
    if (user) {
      const u = { uid: user.uid, email: user.email, phone: user.phoneNumber, provider: user.providerData?.[0]?.providerId || 'email' };
      saveLocalUser(u); callback(u);
    } else { clearLocalUser(); callback(null); }
  });
}

const Auth = {
  config, firebaseConfigured, currentUser, authId, initFirebase,
  signUpEmail, signInEmail, sendPhoneOtp, confirmPhoneOtp, signOut, watchAuth,
};
if (typeof module !== 'undefined') module.exports = Auth;
