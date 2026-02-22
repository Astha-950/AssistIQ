import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path
from datetime import date
import os


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

# check login
if "user" not in st.session_state or not st.session_state.user:
    st.switch_page("app.py")

user_id = st.session_state.user.id

# ─── DATABASE FUNCTIONS ───

def get_tasks(user_id, status=None):
    query = supabase.table("tasks").select("*").eq("user_id", user_id)
    if status:
        query = query.eq("status", status)
    r = query.order("created_at", desc=True).execute()
    return r.data if r.data else []

def complete_task(task_id):
    supabase.table("tasks").update({
        "status": "completed",
        "completed_at": date.today().isoformat()
    }).eq("id", task_id).execute()

def delete_task(task_id):
    supabase.table("tasks").update({
        "status": "removed"
    }).eq("id", task_id).execute()

def add_task_manually(user_id, title, deadline, priority):
    supabase.table("tasks").insert({
        "user_id": user_id,
        "title": title,
        "deadline": deadline,
        "scheduled_date": date.today().isoformat(),
        "priority": priority,
        "status": "pending"
    }).execute()

def check_overdue(tasks):
    today = date.today()
    for task in tasks:
        if task["deadline"] and task["status"] == "pending":
            deadline = date.fromisoformat(task["deadline"])
            if deadline < today:
                supabase.table("tasks").update({
                    "status": "overdue"
                }).eq("id", task["id"]).execute()

# ─── UI ───

st.set_page_config(page_title="Tasks - AssistIQ", page_icon="✅", layout="wide")
st.title("✅ Task Manager")

# check overdue tasks automatically
all_pending = get_tasks(user_id, "pending")
check_overdue(all_pending)

# tabs
tab1, tab2, tab3 = st.tabs(["📋 Pending", "⚠️ Overdue", "✅ Completed"])

with tab1:
    st.subheader("Pending Tasks")
    pending = get_tasks(user_id, "pending")

    if not pending:
        st.info("No pending tasks! Add one below or tell the chat assistant.")
    else:
        for task in pending:
            with st.container():
                col1, col2, col3 = st.columns([5, 1, 1])
                with col1:
                    priority_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task["priority"], "🟡")
                    deadline_text = f"Due: {task['deadline']}" if task["deadline"] else "No deadline"
                    st.markdown(f"{priority_color} **{task['title']}** — {deadline_text}")
                with col2:
                    if st.button("✅ Done", key=f"complete_{task['id']}"):
                        complete_task(task["id"])
                        st.rerun()
                with col3:
                    if st.button("🗑️ Remove", key=f"remove_{task['id']}"):
                        delete_task(task["id"])
                        st.rerun()

    st.markdown("---")
    st.subheader("➕ Add Task Manually")
    with st.form("add_task_form"):
        title = st.text_input("Task Title")
        col1, col2 = st.columns(2)
        with col1:
            deadline = st.date_input("Deadline (optional)", value=None)
        with col2:
            priority = st.selectbox("Priority", ["medium", "high", "low"])
        submitted = st.form_submit_button("Add Task")
        if submitted and title:
            add_task_manually(user_id, title, deadline.isoformat() if deadline else None, priority)
            st.success(f"Task added: {title}")
            st.rerun()

with tab2:
    st.subheader("Overdue Tasks")
    overdue = get_tasks(user_id, "overdue")

    if not overdue:
        st.success("No overdue tasks! Great job.")
    else:
        st.warning(f"You have {len(overdue)} overdue task(s). Complete them as soon as possible!")
        for task in overdue:
            with st.container():
                col1, col2 = st.columns([6, 1])
                with col1:
                    st.markdown(f"🔴 **{task['title']}** — Was due: {task['deadline']}")
                with col2:
                    if st.button("✅ Done", key=f"overdue_complete_{task['id']}"):
                        complete_task(task["id"])
                        st.rerun()

with tab3:
    st.subheader("Completed Tasks")
    completed = get_tasks(user_id, "completed")

    if not completed:
        st.info("No completed tasks yet. Get started!")
    else:
        st.success(f"You have completed {len(completed)} task(s). Keep it up!")
        for task in completed:
            completed_date = task.get("completed_at", "")[:10] if task.get("completed_at") else ""
            st.markdown(f"✅ ~~{task['title']}~~ — Completed: {completed_date}")

st.markdown("---")

# sidebar
with st.sidebar:
    st.markdown("### Navigation")
    if st.button("🏠 Dashboard"):
        st.switch_page("pages/dashboard.py")
    if st.button("💬 Chat"):
        st.switch_page("pages/chat.py")
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.switch_page("app.py")