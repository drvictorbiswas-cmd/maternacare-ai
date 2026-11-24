/* Maternacare AI — device identity & subscription (client-side).
 * IMPORTANT: This is CLIENT-SIDE enforcement only. It can be bypassed by a
 * determined user. Real subscription security requires a backend + Razorpay
 * webhook verification. The UI and README say this clearly.
 */

const PAY_CONFIG = {
  // Paste your Razorpay KEY ID here (safe in client code): e.g. 'rzp_live_xxxx' or 'rzp_test_xxxx'
  razorpayKeyId: 'PASTE_YOUR_RAZORPAY_KEY_ID_HERE',
  // Demo mode: simulate a successful payment without contacting Razorpay.
  demoMode: true,
  // Prices in INR. Update to match your Razorpay plan amounts.
  plans: [
    { id: 'monthly', price: 990, label: 'Monthly' },
    { id: 'yearly', price: 7990, label: 'Yearly (save 32%)' },
  ],
  currency: 'INR',
  companyName: 'Maternacare AI',
  description: 'Full access subscription',
};

const SUBS_KEY = 'mc_subscription';
const DEVICE_KEY = 'mc_device_id';

function getDeviceId() {
  let id = localStorage.getItem(DEVICE_KEY);
  if (!id) {
    id = 'mc_' + (crypto.randomUUID ? crypto.randomUUID() : (Date.now() + '-' + Math.random().toString(36).slice(2)));
    localStorage.setItem(DEVICE_KEY, id);
  }
  return id;
}

function getSubscription() {
  try { return JSON.parse(localStorage.getItem(SUBS_KEY) || 'null'); } catch (_) { return null; }
}

function isSubscribed() {
  const s = getSubscription();
  if (!s || !s.expiresAt) return false;
  if (s.deviceId !== getDeviceId()) return false;
  return new Date(s.expiresAt).getTime() > Date.now();
}

function daysLeft() {
  const s = getSubscription();
  if (!s || !s.expiresAt) return 0;
  return Math.max(0, Math.ceil((new Date(s.expiresAt) - Date.now()) / 86400000));
}

function activateSubscription(planId, paymentId) {
  const plan = PAY_CONFIG.plans.find(p => p.id === planId) || PAY_CONFIG.plans[0];
  const now = new Date();
  const expires = new Date(now);
  if (plan.id === 'yearly') expires.setFullYear(expires.getFullYear() + 1);
  else expires.setMonth(expires.getMonth() + 1);
  const sub = {
    deviceId: getDeviceId(),
    plan: plan.id,
    paymentId: paymentId || 'demo',
    activatedAt: now.toISOString(),
    expiresAt: expires.toISOString(),
  };
  localStorage.setItem(SUBS_KEY, JSON.stringify(sub));
  return sub;
}

function clearSubscription() {
  localStorage.removeItem(SUBS_KEY);
}

/* Open Razorpay checkout. Calls onSuccess(paymentId) / onFail(message). */
function openCheckout(planId, onSuccess, onFail) {
  const plan = PAY_CONFIG.plans.find(p => p.id === planId) || PAY_CONFIG.plans[0];

  if (PAY_CONFIG.demoMode || !PAY_CONFIG.razorpayKeyId.startsWith('rzp_')) {
    // Demo: simulate a short delay and a successful payment.
    setTimeout(() => onSuccess('demo_' + Date.now()), 700);
    return;
  }

  if (typeof Razorpay === 'undefined') {
    onFail('Razorpay checkout could not load. Check your internet connection.');
    return;
  }

  const rzp = new Razorpay({
    key: PAY_CONFIG.razorpayKeyId,
    amount: plan.price * 100, // paise
    currency: PAY_CONFIG.currency,
    name: PAY_CONFIG.companyName,
    description: PAY_CONFIG.description + ' — ' + plan.label,
    notes: { deviceId: getDeviceId() },
    theme: { color: '#0d5c63' },
    handler: function (response) {
      onSuccess(response.razorpay_payment_id);
    },
    modal: { ondismiss: function () { onFail('Payment cancelled.'); } },
  });
  rzp.open();
}

const Payments = { PAY_CONFIG, getDeviceId, getSubscription, isSubscribed, daysLeft, activateSubscription, clearSubscription, openCheckout };
if (typeof module !== 'undefined') module.exports = Payments;
