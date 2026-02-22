import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
from datetime import date
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from core.rollover import run_rollover

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

def get_secret(key):
    try:
        return st.secrets[key]
    except:
        return os.getenv(key)

supabase = create_client(
    get_secret("SUPABASE_URL"),
    get_secret("SUPABASE_KEY")
)

# check if user is logged in
if "user" not in st.session_state or not st.session_state.user:
    st.switch_page("app.py")

user = st.session_state.user
user_id = user.id

# ─── DATABASE FUNCTIONS ───

def get_user(user_id):
    response = supabase.table("users").select("*").eq("id", user_id).execute()
    if response.data:
        return response.data[0]
    return None

def update_streak(user_id, user_data):
    today = date.today()
    last_active = user_data.get("last_active_date")
    current_streak = user_data.get("current_streak", 0)

    if last_active:
        last_active = date.fromisoformat(last_active)
        diff = (today - last_active).days
        if diff == 1:
            current_streak += 1
        elif diff > 1:
            current_streak = 1
    else:
        current_streak = 1

    # reset plan_generated_today if new day
    if last_active and last_active != today:
        supabase.table("users").update({
            "plan_generated_today": False
        }).eq("id", user_id).execute()

    supabase.table("users").update({
        "last_active_date": today.isoformat(),
        "current_streak": current_streak
    }).eq("id", user_id).execute()

    return current_streak

def get_greeting():
    from datetime import datetime
    hour = datetime.now().hour
    if hour < 12:
        return "Good Morning", "☀️", "morning"
    elif hour < 17:
        return "Good Afternoon", "🌤️", "afternoon"
    elif hour < 21:
        return "Good Evening", "🌆", "evening"
    else:
        return "Good Night", "🌙", "night"

def get_pending_tasks(user_id):
    response = supabase.table("tasks").select("*").eq("user_id", user_id).eq("status", "pending").execute()
    return response.data if response.data else []

def get_active_struggles(user_id):
    response = supabase.table("struggles").select("*").eq("user_id", user_id).eq("status", "active").execute()
    return response.data if response.data else []

def check_plan_today(user_id):
    response = supabase.table("users").select("plan_generated_today").eq("id", user_id).execute()
    if response.data:
        return response.data[0].get("plan_generated_today", False)
    return False

# ─── UI STARTS HERE ───

st.set_page_config(page_title="Dashboard - AssistIQ", page_icon="🧠", layout="wide")

user_data = get_user(user_id)

# run rollover every time dashboard opens
flagged_tasks = run_rollover(supabase, user_id)

streak = update_streak(user_id, user_data)
greeting, emoji, time_of_day = get_greeting()
plan_done = check_plan_today(user_id)
pending_tasks = get_pending_tasks(user_id)
active_struggles = get_active_struggles(user_id)

# header
st.title(f"{emoji} {greeting}, {user_data.get('name', 'there')}!")
st.markdown("---")

# show flagged tasks warning
if flagged_tasks:
    st.warning("⚠️ These tasks have been rolling over for 5+ days:")
    for title in flagged_tasks:
        st.markdown(f"- **{title}**")
    st.info("Go to Tasks page to complete or remove them.")

# streak
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("🔥 Current Streak", f"{streak} days")
with col2:
    st.metric("✅ Pending Tasks", len(pending_tasks))
with col3:
    st.metric("💪 Active Struggles", len(active_struggles))

st.markdown("---")

# smart message based on time and plan status
st.subheader("📋 Today's Status")

if time_of_day == "morning":
    if not plan_done:
        st.warning("You haven't planned your day yet!")
        if st.button("🗓️ Generate Today's Plan", use_container_width=True):
            st.switch_page("pages/planner.py")
    else:
        st.success("Great! Your day is planned. Stay focused!")

elif time_of_day == "afternoon":
    if not plan_done:
        st.warning("It's afternoon and no plan yet. Let's make a shorter plan!")
        if st.button("🗓️ Plan Remaining Day", use_container_width=True):
            st.switch_page("pages/planner.py")
    else:
        st.info(f"You have {len(pending_tasks)} tasks remaining today. Keep going!")

elif time_of_day == "evening":
    if not plan_done:
        st.warning("Didn't plan today? Let's set up tomorrow instead!")
        if st.button("🗓️ Plan Tomorrow", use_container_width=True):
            st.switch_page("pages/planner.py")
    else:
        st.info("Evening check-in time! Head to Chat and tell me how your day went.")

else:
    st.info("Late night! Let's plan tomorrow so you start fresh.")
    if st.button("🗓️ Plan Tomorrow", use_container_width=True):
        st.switch_page("pages/planner.py")

st.markdown("---")

# quick navigation
st.subheader("⚡ Quick Actions")

c1, c2, c3, c4 = st.columns(4)
with c1:
    if st.button("💬 Chat", use_container_width=True):
        st.switch_page("pages/chat.py")
with c2:
    if st.button("✅ Tasks", use_container_width=True):
        st.switch_page("pages/tasks.py")
with c3:
    if st.button("💪 Struggles", use_container_width=True):
        st.switch_page("pages/struggles.py")
with c4:
    if st.button("📚 Notes", use_container_width=True):
        st.switch_page("pages/notes.py")

st.markdown("---")

if st.button("🚪 Logout"):
    st.session_state.clear()
    st.switch_page("app.py")