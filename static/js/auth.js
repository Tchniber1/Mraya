// Google sign-in with Firebase Auth, then exchange the ID token for a Django session.
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

const config = JSON.parse(document.getElementById("firebase-config").textContent);
const auth = getAuth(initializeApp(config));
const provider = new GoogleAuthProvider();
provider.setCustomParameters({ prompt: "select_account" });

const button = document.getElementById("google-signin");
const errorBox = document.getElementById("auth-error");

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}

button.addEventListener("click", async () => {
  button.disabled = true;
  errorBox.classList.add("hidden");
  try {
    const result = await signInWithPopup(auth, provider);
    const idToken = await result.user.getIdToken();
    const data = await window.Mraya.postJSON("/accounts/session/", { idToken });
    window.location.assign(data.redirect || "/");
  } catch (err) {
    if (err && err.code === "auth/popup-closed-by-user") {
      showError("Sign-in was cancelled.");
    } else {
      showError(err.message || "Sign-in failed. Please try again.");
    }
    button.disabled = false;
  }
});
