/**
 * Artemis Plus web unlock — Cloudflare Worker.
 *
 * Lets a user who bought Artemis Plus in the app read premium articles on
 * artemistracker.app. The app opens /web-unlock with its RevenueCat app
 * user ID; this worker verifies the entitlement against the RevenueCat
 * REST API and hands the browser a signed, expiring token. The website
 * then calls /web-verify to validate the token before rendering full
 * premium bodies.
 *
 * Routes (bind this worker to both, or merge into the existing api worker):
 *   api.artemistracker.app/web-unlock*
 *   api.artemistracker.app/web-verify*
 *
 * Required environment variables (Worker settings → Variables, encrypt both):
 *   RC_SECRET_KEY          RevenueCat secret API key (sk_...)
 *   UNLOCK_SIGNING_SECRET  any long random string, e.g. `openssl rand -hex 32`
 *
 * Flow:
 *   app  → GET /web-unlock?uid={rcAppUserID}
 *   ↳ RC check: entitlement "artemis_pro" active?
 *     yes → 302 https://artemistracker.app/unlock#t={uid_b64}.{exp}.{sig}
 *     no  → 302 https://artemistracker.app/unlock#t=denied
 *   site → GET /web-verify?token=...   → {"valid":true|false}
 *
 * Tokens expire after 30 days; the site re-runs the unlock link from the
 * app to renew. Revocation happens naturally: /web-verify re-signs only,
 * so to force re-checks against RevenueCat, lower TOKEN_TTL_DAYS.
 */

const SITE = 'https://artemistracker.app';
const ENTITLEMENT_ID = 'artemis_pro';
const TOKEN_TTL_DAYS = 30;

const CORS = {
  'Access-Control-Allow-Origin': SITE,
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Max-Age': '86400',
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === 'OPTIONS') return new Response(null, { headers: CORS });
    if (url.pathname === '/web-unlock') return handleUnlock(url, env);
    if (url.pathname === '/web-verify') return handleVerify(url, env);
    return new Response('Not found', { status: 404 });
  },
};

async function handleUnlock(url, env) {
  const uid = url.searchParams.get('uid');
  if (!uid || uid.length > 200) return redirectWithToken('denied');

  let active = false;
  try {
    const res = await fetch(
      'https://api.revenuecat.com/v1/subscribers/' + encodeURIComponent(uid),
      { headers: { Authorization: 'Bearer ' + env.RC_SECRET_KEY } }
    );
    if (res.ok) {
      const data = await res.json();
      const ent = data.subscriber?.entitlements?.[ENTITLEMENT_ID];
      // expires_date null = lifetime; otherwise must be in the future.
      active = !!ent && (ent.expires_date === null || Date.parse(ent.expires_date) > Date.now());
    }
  } catch (_) {
    active = false;
  }

  if (!active) return redirectWithToken('denied');

  const exp = Date.now() + TOKEN_TTL_DAYS * 86400 * 1000;
  const sig = await hmac(`${uid}|${exp}`, env.UNLOCK_SIGNING_SECRET);
  const token = `${b64url(uid)}.${exp}.${sig}`;
  return redirectWithToken(token);
}

async function handleVerify(url, env) {
  const token = url.searchParams.get('token') || '';
  const parts = token.split('.');
  let valid = false;
  if (parts.length === 3) {
    const uid = b64urlDecode(parts[0]);
    const exp = parseInt(parts[1], 10);
    if (uid && exp > Date.now()) {
      const expected = await hmac(`${uid}|${exp}`, env.UNLOCK_SIGNING_SECRET);
      valid = timingSafeEqual(expected, parts[2]);
    }
  }
  return new Response(JSON.stringify({ valid }), {
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', ...CORS },
  });
}

function redirectWithToken(token) {
  return Response.redirect(`${SITE}/unlock#t=${token}`, 302);
}

async function hmac(message, secret) {
  const key = await crypto.subtle.importKey(
    'raw', new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
  );
  const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(message));
  return [...new Uint8Array(sig)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

function timingSafeEqual(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function b64url(s) {
  return btoa(unescape(encodeURIComponent(s))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function b64urlDecode(s) {
  try {
    return decodeURIComponent(escape(atob(s.replace(/-/g, '+').replace(/_/g, '/'))));
  } catch (_) {
    return null;
  }
}
