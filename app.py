# app.py (Frontend)
import streamlit as st
import requests
import os

# ── Page Configuration ────────────────────────────────────────────────

st.set_page_config(
    page_title="Cogniva",
    page_icon="🧠",
    layout="centered"
)

# ── API URL (RAILWAY SAFE METHOD) ─────────────────────────────────────

# In production: set API_URL in Railway frontend service env vars
API_URL = os.getenv("API_URL")

# Fallback ONLY for local development
if not API_URL:
    API_URL = "http://127.0.0.1:5000/process_turn"

BASE_URL = API_URL.replace("/process_turn", "")

# ── SESSION STATE ─────────────────────────────────────────────────────

defaults = {
    "student_id": None,
    "student_name": None,
    "logged_in": False,
    "messages": [],
    "session_mode": "onboarding",
    "self_report_done": False,
    "returning_user": False
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ═════════════════════════════════════════════════════════════════════
# LOGIN SCREEN
# ═════════════════════════════════════════════════════════════════════

if not st.session_state.logged_in:

    st.title("🧠 Cogniva")
    st.caption("Adaptive Learning Intelligence")
    st.markdown("---")

    st.markdown("### Welcome to Cogniva")

    with st.form("login_form"):
        name = st.text_input("Your first name")
        email = st.text_input("Your university email")
        submitted = st.form_submit_button("Enter Cogniva →")

        if submitted:

            if not name.strip() or not email.strip():
                st.error("Enter both name and email")

            elif "@" not in email:
                st.error("Invalid email")

            else:
                student_id = email.strip().lower()

                try:
                    r = requests.get(
                        f"{BASE_URL}/get_profile/{student_id}",
                        timeout=10
                    )

                    if r.status_code == 200:
                        data = r.json()
                        if data.get("exists"):
                            st.session_state.returning_user = True
                            st.session_state.session_mode = "learning"
                        else:
                            st.session_state.returning_user = False
                            st.session_state.session_mode = "onboarding"

                except Exception:
                    st.session_state.returning_user = False
                    st.session_state.session_mode = "onboarding"

                st.session_state.student_id = student_id
                st.session_state.student_name = name.strip()
                st.session_state.logged_in = True

                st.rerun()

# ═════════════════════════════════════════════════════════════════════
# MAIN APP
# ═════════════════════════════════════════════════════════════════════

else:

    st.title("🧠 Cogniva")

    st.caption(
        f"Welcome back, {st.session_state.student_name}"
        if st.session_state.returning_user
        else f"Hello, {st.session_state.student_name}"
    )

    st.markdown("---")

    # ── Auto-Trigger Onboarding ────────────────────────────────────
    
    if len(st.session_state.messages) == 0 and st.session_state.session_mode == "onboarding":
        with st.spinner("Initializing Cogniva Profile..."):
            try:
                res = requests.post(
                    API_URL,
                    json={
                        "student_id": st.session_state.student_id,
                        "message": "Hello, I am a new student. Please start my onboarding.",
                        "session_mode": "onboarding"
                    },
                    timeout=30
                )
                res.raise_for_status()
                data = res.json()
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": data.get("reply", "Let's begin.")
                })
            except Exception:
                st.error("Failed to connect to backend to start onboarding.")

    # ── Chat History ───────────────────────────────────────────────

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── Input ──────────────────────────────────────────────────────

    prompt = st.chat_input("Type your message...")

    if prompt:

        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })

        with st.chat_message("user"):
            st.markdown(prompt)

        payload = {
            "student_id": st.session_state.student_id,
            "message": prompt,
            "session_mode": st.session_state.session_mode
        }

        with st.spinner("Cogniva is thinking..."):

            try:
                res = requests.post(
                    API_URL,
                    json=payload,
                    timeout=30
                )

                res.raise_for_status()
                data = res.json()

                reply = data.get("reply", "No response")
                inferred = data.get("inferred_states")
                done = data.get("onboarding_complete", False)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": reply
                })

                with st.chat_message("assistant"):
                    st.markdown(reply)

                if done:
                    st.session_state.session_mode = "learning"
                    st.success("Onboarding complete")
                    st.rerun()

                if inferred and st.session_state.session_mode == "learning":
                    with st.expander("Cognitive State"):
                        st.write(inferred)

            except requests.exceptions.ConnectionError:
                st.error("Backend not reachable (API_URL incorrect or backend down)")

            except requests.exceptions.Timeout:
                st.error("Request timed out")

            except Exception as e:
                st.error(f"Error: {e}")

# ── SIDEBAR ──────────────────────────────────────────────────────────

st.sidebar.title("Session")

st.sidebar.write(st.session_state.student_name)
st.sidebar.write(st.session_state.student_id)

st.sidebar.write(
    "Mode:",
    st.session_state.session_mode
)

# ── SIGN OUT ──────────────────────────────────────────────────────────

if st.sidebar.button("Logout"):

    for k in list(st.session_state.keys()):
        del st.session_state[k]

    st.rerun()
