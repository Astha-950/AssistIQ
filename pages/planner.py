import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path
from datetime import date
from groq import Groq
import os

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# check login
if "user" not in st.session_state or not st.session_state.user:
    st.switch_page("app.py")

user_id = st.session_state.user.id

# ─── DATABASE FUNCTIONS ───

def get_user(user_id):
    r = supabase.table("users").select("*").eq("id", user_id).execute()
    return r.data[0] if r.data else {}

def get_pending_tasks(user_id):
    r = supabase.table("tasks").select("*").eq("user_id", user_id).eq("status", "pending").order("created_at").execute()
    return r.data if r.data else []

def get_overdue_tasks(user_id):
    r = supabase.table("tasks").select("*").eq("user_id", user_id).eq("status", "overdue").execute()
    return r.data if r.data else []

def get_active_struggles(user_id):
    r = supabase.table("struggles").select("*").eq("user_id", user_id).eq("status", "active").order("confidence_score").execute()
    return r.data if r.data else []

def save_plan(user_id, plan):
    supabase.table("users").update({
        "plan_generated_today": True,
        "todays_plan": plan,
        "plan_date": date.today().isoformat()
    }).eq("id", user_id).execute()

def get_saved_plan(user_id):
    r = supabase.table("users").select("todays_plan, plan_date, plan_generated_today").eq("id", user_id).execute()
    if r.data:
        data = r.data[0]
        plan_date = data.get("plan_date")
        if plan_date and plan_date == date.today().isoformat():
            return data.get("todays_plan")
    return None

def get_time_of_day():
    from datetime import datetime
    hour = datetime.now().hour
    if hour < 12:
        return "morning"
    elif hour < 17:
        return "afternoon"
    elif hour < 21:
        return "evening"
    else:
        return "night"

# ─── PLANNER FUNCTION ───

def generate_plan(user_data, pending_tasks, overdue_tasks, struggles, time_of_day):
    overdue_text = "\n".join([f"- {t['title']} (was due: {t['deadline']})" for t in overdue_tasks]) if overdue_tasks else "None"

    pending_text = "\n".join([
        f"- {t['title']} (priority: {t['priority']}, deadline: {t.get('deadline', 'no deadline')})"
        for t in pending_tasks[:6]
    ]) if pending_tasks else "None"

    struggles_text = "\n".join([
        f"- {s['topic']} (confidence: {s['confidence_score']}/10)"
        for s in struggles[:5]
    ]) if struggles else "None"

    prompt = f"""You are AssistIQ, a personal productivity assistant for a student preparing for jobs.

User: {user_data.get('name', 'Student')}
Time of day: {time_of_day}
Today's date: {date.today().isoformat()}

Overdue tasks (complete these first):
{overdue_text}

Pending tasks:
{pending_text}

Active struggles (topics to study):
{struggles_text}

Create a realistic, motivating day plan for the {time_of_day}.
- If morning: plan full day hour by hour
- If afternoon: plan remaining hours
- If evening: focus on review and tomorrow prep
- If night: just plan tomorrow

Rules:
- Overdue tasks must come first
- Pick max 3-4 tasks for today (don't overwhelm)
- Pick max 2 struggle topics to study today (lowest confidence first)
- Be specific with time slots
- Keep it motivating and realistic
- End with an encouraging message

Format it nicely with emojis and time slots."""

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# ─── UI ───

st.set_page_config(page_title="Planner - AssistIQ", page_icon="🗓️", layout="wide")
st.title("🗓️ Daily Planner")

user_data = get_user(user_id)
pending_tasks = get_pending_tasks(user_id)
overdue_tasks = get_overdue_tasks(user_id)
active_struggles = get_active_struggles(user_id)
time_of_day = get_time_of_day()

# summary cards
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📋 Pending Tasks", len(pending_tasks))
with col2:
    st.metric("⚠️ Overdue Tasks", len(overdue_tasks))
with col3:
    st.metric("💪 Active Struggles", len(active_struggles))

st.markdown("---")

# show overdue warning
if overdue_tasks:
    st.error(f"⚠️ You have {len(overdue_tasks)} overdue task(s)! These will be prioritized in your plan.")

# load plan from database
saved_plan = get_saved_plan(user_id)

if saved_plan:
    if "preview_plan" in st.session_state and st.session_state.preview_plan:
        st.subheader("🆕 New Plan Preview")
        st.markdown(st.session_state.preview_plan)
        st.markdown("---")
        st.warning("Do you want to save this new plan or keep your previous one?")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Save This Plan", use_container_width=True, type="primary"):
                save_plan(user_id, st.session_state.preview_plan)
                st.session_state.preview_plan = None
                st.success("New plan saved!")
                st.rerun()
        with col2:
            if st.button("↩️ Keep Previous Plan", use_container_width=True):
                st.session_state.preview_plan = None
                st.info("Keeping your previous plan.")
                st.rerun()
    else:
        st.subheader("📋 Today's Plan")
        st.markdown(saved_plan)
        st.markdown("---")

        if st.button("🔄 Regenerate Plan", use_container_width=True):
            with st.spinner("Creating new plan..."):
                plan = generate_plan(
                    user_data, pending_tasks,
                    overdue_tasks, active_struggles, time_of_day
                )
                # don't save yet — show preview first
                st.session_state.preview_plan = plan
                st.rerun()

else:
    st.subheader(f"Ready to plan your {time_of_day}?")

    if not pending_tasks and not active_struggles:
        st.info("No tasks or struggles found. Add some via chat first!")
    else:
        if st.button("🗓️ Generate My Plan", use_container_width=True, type="primary"):
            with st.spinner("Creating your personalized plan..."):
                plan = generate_plan(
                    user_data, pending_tasks,
                    overdue_tasks, active_struggles, time_of_day
                )
                # first time — save directly, no preview needed
                save_plan(user_id, plan)
                st.rerun()

# evening checkin
st.markdown("---")
st.subheader("🌆 Evening Check-in")
st.caption("Tell me how your day went and I will update your tasks automatically")

if st.button("💬 Go to Chat for Check-in"):
    st.switch_page("pages/chat.py")

# sidebar
with st.sidebar:
    st.markdown("### Navigation")
    if st.button("🏠 Dashboard"):
        st.switch_page("pages/dashboard.py")
    if st.button("💬 Chat"):
        st.switch_page("pages/chat.py")
    if st.button("✅ Tasks"):
        st.switch_page("pages/tasks.py")
    if st.button("💪 Struggles"):
        st.switch_page("pages/struggles.py")
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.switch_page("app.py")