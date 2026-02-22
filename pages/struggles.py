import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path
from datetime import date
import os

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# check login
if "user" not in st.session_state or not st.session_state.user:
    st.switch_page("app.py")

user_id = st.session_state.user.id

# ─── DATABASE FUNCTIONS ───

def get_struggles(user_id, status="active"):
    r = supabase.table("struggles").select("*").eq("user_id", user_id).eq("status", status).order("confidence_score").execute()
    return r.data if r.data else []

def resolve_struggle(struggle_id):
    supabase.table("struggles").update({
        "status": "resolved",
        "resolved_at": date.today().isoformat()
    }).eq("id", struggle_id).execute()

def add_struggle_manually(user_id, topic, confidence_score):
    existing = supabase.table("struggles").select("*").eq("user_id", user_id).eq("topic", topic).eq("status", "active").execute()
    if not existing.data:
        supabase.table("struggles").insert({
            "user_id": user_id,
            "topic": topic,
            "confidence_score": confidence_score
        }).execute()
        return True
    return False

def get_confidence_label(score):
    if score <= 3:
        return "🔴 Weak"
    elif score <= 6:
        return "🟡 Improving"
    else:
        return "🟢 Almost There"

# ─── UI ───

st.set_page_config(page_title="Struggles - AssistIQ", page_icon="💪", layout="wide")
st.title("💪 Struggle Tracker")
st.caption("Topics you are working to master. Tell the chat assistant your progress and confidence will update automatically.")

tab1, tab2 = st.tabs(["🔥 Active Struggles", "✅ Resolved"])

with tab1:
    active = get_struggles(user_id, "active")

    if not active:
        st.success("No active struggles! You are on top of everything.")
    else:
        # check if any topic needs attention (confidence >= 7)
        flag_topics = [s for s in active if s["confidence_score"] >= 7]
        if flag_topics:
            for t in flag_topics:
                st.success(f"🎉 Your confidence in **{t['topic']}** is now {t['confidence_score']}/10. Are you comfortable with it now?")
                if st.button(f"✅ Mark {t['topic']} as Resolved", key=f"resolve_flag_{t['id']}"):
                    resolve_struggle(t["id"])
                    st.rerun()

        st.markdown("---")

        # show all active struggles
        for struggle in active:
            with st.container():
                col1, col2, col3 = st.columns([4, 2, 2])

                with col1:
                    label = get_confidence_label(struggle["confidence_score"])
                    st.markdown(f"**{struggle['topic']}** — {label}")
                    st.progress(struggle["confidence_score"] / 10)

                with col2:
                    st.markdown(f"**{struggle['confidence_score']}/10**")
                    st.caption("Confidence Score")

                with col3:
                    if st.button("✅ Resolved", key=f"resolve_{struggle['id']}"):
                        resolve_struggle(struggle["id"])
                        st.rerun()

                st.markdown("---")

    # add manually
    st.subheader("➕ Add Struggle Manually")
    with st.form("add_struggle_form"):
        topic = st.text_input("Topic Name (e.g. Dynamic Programming)")
        confidence = st.slider("Current Confidence", min_value=1, max_value=10, value=2)
        submitted = st.form_submit_button("Add Struggle")
        if submitted and topic:
            added = add_struggle_manually(user_id, topic, confidence)
            if added:
                st.success(f"Added: {topic}")
                st.rerun()
            else:
                st.warning(f"{topic} is already in your active struggles!")

with tab2:
    resolved = get_struggles(user_id, "resolved")

    if not resolved:
        st.info("No resolved struggles yet. Keep working!")
    else:
        st.success(f"You have mastered {len(resolved)} topic(s)! 🎉")
        for struggle in resolved:
            resolved_date = struggle.get("resolved_at", "")[:10] if struggle.get("resolved_at") else ""
            st.markdown(f"✅ ~~{struggle['topic']}~~ — Resolved: {resolved_date}")

# sidebar
with st.sidebar:
    st.markdown("### Navigation")
    if st.button("🏠 Dashboard"):
        st.switch_page("pages/dashboard.py")
    if st.button("💬 Chat"):
        st.switch_page("pages/chat.py")
    if st.button("✅ Tasks"):
        st.switch_page("pages/tasks.py")
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.switch_page("app.py")