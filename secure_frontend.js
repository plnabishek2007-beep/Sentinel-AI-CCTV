/**
 * secure_frontend.js
 * Sentinel AI CCTV — Secure Frontend Helpers
 *
 * Include this script in your HTML and call initSecureFrontend()
 * after the DOM is ready.
 */

// ── STEP 3 & 4: Secure API Key handling ─────────────────────────────────────

let API_KEY = null;

function initSecureFrontend() {
  // Prompt once; persist in sessionStorage (cleared when tab closes)
  API_KEY = sessionStorage.getItem("sentinel_api_key");

  if (!API_KEY) {
    API_KEY = prompt("🔐 Enter API Key to access Sentinel AI:");
    if (!API_KEY) {
      document.body.innerHTML = "<h2>Access denied. Reload to try again.</h2>";
      return;
    }
    sessionStorage.setItem("sentinel_api_key", API_KEY);
  }

  // ── STEP 3: Protect camera stream ─────────────────────────────────────────
  const videoEl = document.getElementById("video");
  if (videoEl) {
    videoEl.src = "/stream?api_key=" + encodeURIComponent(API_KEY);
  }

  // Start polling status
  fetchStatus();
  setInterval(fetchStatus, 3000);
}

// ── STEP 4: Secure fetch helpers ─────────────────────────────────────────────

function fetchStatus() {
  fetch("/status", {
    headers: { "x-api-key": API_KEY }
  })
    .then(res => {
      if (res.status === 401) { handleUnauthorized(); return null; }
      return res.json();
    })
    .then(data => {
      if (!data) return;
      // Update your UI with data here
      console.log("Status:", data);
    })
    .catch(err => console.error("Status fetch error:", err));
}

function sendControl(camera, alerts) {
  fetch("/control", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": API_KEY
    },
    body: JSON.stringify({ camera, alerts })
  })
    .then(res => {
      if (res.status === 401) { handleUnauthorized(); return null; }
      return res.json();
    })
    .then(data => {
      if (!data) return;
      console.log("Control response:", data);
    })
    .catch(err => console.error("Control fetch error:", err));
}

function handleUnauthorized() {
  sessionStorage.removeItem("sentinel_api_key");
  alert("❌ Invalid API Key. Please reload and try again.");
  location.reload();
}

// ── STEP 7: Consent banner ────────────────────────────────────────────────────

function injectConsentBanner() {
  const container = document.querySelector(".video-container") || document.body;
  const banner = document.createElement("div");
  banner.innerHTML = "⚠️ AI Surveillance Active (Consent Required)";
  Object.assign(banner.style, {
    position: "absolute",
    bottom: "10px",
    left: "10px",
    background: "red",
    color: "white",
    padding: "6px 10px",
    borderRadius: "8px",
    fontSize: "12px",
    fontWeight: "bold",
    zIndex: "999",
    pointerEvents: "none"
  });
  container.style.position = "relative";
  container.appendChild(banner);
}

// Auto-init when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  initSecureFrontend();
  injectConsentBanner();
});
