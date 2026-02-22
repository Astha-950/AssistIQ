import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
import os
import json
from datetime import date
from pathlib import Path
from groq import Groq

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

groq_client = Groq(api_key=get_secret("GROQ_API_KEY"))

# check login
if "user" not in st.session_state or not st.session_state.user:
    st.switch_page("app.py")

user = st.session_state.user
user_id = user.id

# ─── DATABASE FUNCTIONS ───

def get_user(user_id):
    r = supabase.table("users").select("*").eq("id", user_id).execute()
    return r.data[0] if r.data else {}

def get_pending_tasks(user_id):
    r = supabase.table("tasks").select("*").eq("user_id", user_id).eq("status", "pending").execute()
    return r.data if r.data else []

def get_active_struggles(user_id):
    r = supabase.table("struggles").select("*").eq("user_id", user_id).eq("status", "active").execute()
    return r.data if r.data else []

def add_task(user_id, title, deadline=None, priority="medium"):
    supabase.table("tasks").insert({
        "user_id": user_id,
        "title": title,
        "deadline": deadline,
        "scheduled_date": date.today().isoformat(),
        "priority": priority,
        "status": "pending"
    }).execute()

def add_struggle(user_id, topic, confidence_score=2):
    existing = supabase.table("struggles").select("*").eq("user_id", user_id).eq("topic", topic).eq("status", "active").execute()
    if not existing.data:
        supabase.table("struggles").insert({
            "user_id": user_id,
            "topic": topic,
            "confidence_score": confidence_score
        }).execute()

def update_struggle_confidence(user_id, topic, change):
    existing = supabase.table("struggles").select("*").eq("user_id", user_id).eq("topic", topic).eq("status", "active").execute()
    if existing.data:
        struggle = existing.data[0]
        new_score = min(10, max(1, struggle["confidence_score"] + change))
        supabase.table("struggles").update({
            "confidence_score": new_score
        }).eq("id", struggle["id"]).execute()

def complete_task_by_title(user_id, title_keyword):
    tasks = supabase.table("tasks").select("*").eq("user_id", user_id).eq("status", "pending").execute()
    if tasks.data:
        for task in tasks.data:
            if title_keyword.lower() in task["title"].lower():
                supabase.table("tasks").update({
                    "status": "completed",
                    "completed_at": date.today().isoformat()
                }).eq("id", task["id"]).execute()
                return task["title"]
    return None

# ─── GROQ FUNCTIONS ───

def build_system_prompt(user_data, tasks, struggles):
    tasks_text = "\n".join([f"- {t['title']} (priority: {t['priority']}, deadline: {t.get('deadline', 'none')})" for t in tasks]) if tasks else "No pending tasks"
    struggles_text = "\n".join([f"- {s['topic']} (confidence: {s['confidence_score']}/10)" for s in struggles]) if struggles else "No active struggles"

    return f"""You are AssistIQ, a personal productivity assistant for a student preparing for jobs.

User: {user_data.get('name', 'Student')}

Current pending tasks:
{tasks_text}

Current active struggles:
{struggles_text}

Your job:
1. Answer questions naturally and helpfully
2. When user mentions a new task, extract it and return it as JSON
3. When user mentions struggling with a topic, extract it and return as JSON
4. When user says they completed something, extract it and return as JSON
5. When user mentions doing well in a topic, increase confidence and return as JSON

Always respond in this format when you detect an action:
First give your natural conversational response.
Then at the very end if there is an action, add a JSON block like this:

```json
{{
  "action": "add_task" | "add_struggle" | "complete_task" | "update_confidence",
  "data": {{
    "title": "task title",
    "deadline": "YYYY-MM-DD",
    "priority": "high/medium/low",
    "topic": "topic name",
    "confidence_score": 2,
    "change": 1,
    "keyword": "keyword"
  }}
}}
```

If no action needed, just respond normally without JSON.
Today's date is {date.today().isoformat()}.
"""

def extract_and_handle_action(response_text, user_id):
    try:
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            json_str = response_text[json_start:json_end].strip()
            action_data = json.loads(json_str)

            action = action_data.get("action")
            data = action_data.get("data", {})

            if action == "add_task":
                add_task(user_id, data["title"], data.get("deadline"), data.get("priority", "medium"))
                return f"✅ Task added: **{data['title']}**"

            elif action == "add_struggle":
                add_struggle(user_id, data["topic"], data.get("confidence_score", 2))
                return f"💪 Added to struggles: **{data['topic']}**"

            elif action == "complete_task":
                completed = complete_task_by_title(user_id, data["keyword"])
                if completed:
                    return f"✅ Marked as complete: **{completed}**"

            elif action == "update_confidence":
                update_struggle_confidence(user_id, data["topic"], data.get("change", 1))
                return f"📈 Updated confidence for: **{data['topic']}**"

    except Exception as e:
        pass
    return None

def chat_with_groq(messages, user_data, tasks, struggles):
    system = build_system_prompt(user_data, tasks, struggles)
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=1000,
        messages=[{"role": "system", "content": system}] + messages
    )
    return response.choices[0].message.content

# ─── UI ───

st.set_page_config(page_title="Chat - AssistIQ", page_icon="💬", layout="wide")
st.title("💬 Chat with AssistIQ")

user_data = get_user(user_id)
tasks = get_pending_tasks(user_id)
struggles = get_active_struggles(user_id)

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Talk to your assistant..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            groq_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
            response = chat_with_groq(groq_messages, user_data, tasks, struggles)

            display_response = response
            if "```json" in response:
                display_response = response[:response.find("```json")].strip()

            st.markdown(display_response)

            action_result = extract_and_handle_action(response, user_id)
            if action_result:
                st.success(action_result)

    st.session_state.messages.append({"role": "assistant", "content": display_response})

with st.sidebar:
    st.markdown("### Quick Info")
    st.markdown(f"**Pending Tasks:** {len(tasks)}")
    st.markdown(f"**Active Struggles:** {len(struggles)}")
    st.markdown("---")
    if st.button("🏠 Dashboard"):
        st.switch_page("pages/dashboard.py")
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.switch_page("app.py")