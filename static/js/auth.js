// Google sign-in with Firebase Auth, then exchange the ID token for a Django session.
// Two modes:
//   * default: Firebase popup (served from <project>.firebaseapp.com)
//   * GOOGLE_OAUTH_CLIENT_ID set: Google Identity Services button -> signInWithCredential,
//     which only talks to accounts.google.com / googleapis.com (works where firebaseapp.com is blocked)
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import {
  getAuth,
  GoogleAuthProvider,
  signInWithCredential,
  signInWithPopup,
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

const { googleClientId, ...config } = JSON.parse(document.getElementById("firebase-config").textContent);
const auth = getAuth(initializeApp(config));

const button = document.getElementById("google-signin");
const errorBox = document.getElementById("auth-error");

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}

async function finishSignIn(user) {
  const idToken = await user.getIdToken();
  const data = await window.Mraya.postJSON("/accounts/session/", { idToken });
  window.location.assign(data.redirect || "/");
}

function usePopup() {
  const provider = new GoogleAuthProvider();
  provider.setCustomParameters({ prompt: "select_account" });
  button.addEventListener("click", async () => {
    button.disabled = true;
    errorBox.classList.add("hidden");
    try {
      const result = await signInWithPopup(auth, provider);
      await finishSignIn(result.user);
    } catch (err) {
      showError(err && err.code === "auth/popup-closed-by-user"
        ? "Sign-in was cancelled."
        : (err.message || "Sign-in failed. Please try again."));
      button.disabled = false;
    }
  });
}

function useGoogleIdentityServices() {
  const script = document.createElement("script");
  script.src = "https://accounts.google.com/gsi/client";
  script.async = true;
  script.onerror = () => showError("Could not load Google sign-in. Check your connection.");
  script.onload = () => {
    google.accounts.id.initialize({
      client_id: googleClientId,
      callback: async (response) => {
        errorBox.classList.add("hidden");
        try {
          const credential = GoogleAuthProvider.credential(response.credential);
          const result = await signInWithCredential(auth, credential);
          await finishSignIn(result.user);
        } catch (err) {
          showError(err.message || "Sign-in failed. Please try again.");
        }
      },
    });
    const slot = document.createElement("div");
    slot.style.display = "flex";
    slot.style.justifyContent = "center";
    button.replaceWith(slot);
    google.accounts.id.renderButton(slot, { theme: "outline", size: "large", shape: "pill", text: "continue_with", width: 320 });
  };
  document.head.appendChild(script);
}

if (googleClientId) {
  useGoogleIdentityServices();
} else {
  usePopup();
}
