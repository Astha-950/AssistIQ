import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path
from groq import Groq
import os
import tempfile
import sys

sys.path.append(str(Path(__file__).parent.parent))

from core.rag import (
    extract_text_from_pdf,
    add_document_to_index,
    search_index
)
from core.notion import get_notion_pages, get_page_content

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

def save_note_to_db(user_id, filename, source, content):
    supabase.table("notes").insert({
        "user_id": user_id,
        "file_name": filename,
        "source": source,
        "content": content[:500]  # save preview
    }).execute()

def get_notes(user_id):
    r = supabase.table("notes").select("*").eq("user_id", user_id).execute()
    return r.data if r.data else []

# ─── ANSWER FROM NOTES ───

def answer_from_notes(user_id, question):
    context = search_index(user_id, question)

    if context:
        prompt = f"""You are a helpful study assistant.
Answer the question using ONLY the context below.
If the answer is not in the context, say exactly:
"I couldn't find this in your notes. Here's what I know from general knowledge:"
and then answer from your own knowledge.

Context from user's notes:
{context}

Question: {question}"""
    else:
        prompt = f"""You are a helpful study assistant.
The user asked: {question}
There are no relevant notes found.
Say: "I couldn't find this in your notes. Here's what I know from general knowledge:"
Then answer from your own knowledge."""

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# ─── UI ───

st.set_page_config(page_title="Notes - AssistIQ", page_icon="📚", layout="wide")
st.title("📚 Notes & RAG")
st.caption("Upload your notes and ask questions from them")

tab1, tab2, tab3 = st.tabs(["📄 Upload PDF", "🔗 Notion", "❓ Ask Question"])

# ── TAB 1: PDF Upload ──
with tab1:
    st.subheader("Upload PDF Notes")
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

    if uploaded_file:
        if st.button("📥 Process PDF", use_container_width=True):
            with st.spinner("Reading and indexing your PDF..."):
                # save to temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.read())
                    tmp_path = tmp.name

                # extract text
                text = extract_text_from_pdf(tmp_path)

                if text.strip():
                    # add to chromadb
                    add_document_to_index(user_id, text, uploaded_file.name, "pdf")
                    # save to supabase
                    save_note_to_db(user_id, uploaded_file.name, "pdf", text)
                    st.success(f"✅ {uploaded_file.name} indexed successfully!")
                else:
                    st.error("Could not extract text from PDF. Make sure it is not a scanned image.")

                # cleanup temp file
                os.unlink(tmp_path)

    # show uploaded notes
    st.markdown("---")
    st.subheader("📁 Your Uploaded Notes")
    notes = get_notes(user_id)
    pdf_notes = [n for n in notes if n["source"] == "pdf"]

    if not pdf_notes:
        st.info("No PDFs uploaded yet.")
    else:
        for note in pdf_notes:
            st.markdown(f"📄 **{note['file_name']}** — Uploaded: {note['uploaded_at'][:10]}")

# ── TAB 2: Notion ──
with tab2:
    st.subheader("Connect Notion")
    st.caption("Enter your Notion API key to fetch your pages")

    notion_key = st.text_input(
        "Notion API Key",
        type="password",
        placeholder="secret_xxxxxxxx",
        help="Get it from https://www.notion.so/my-integrations"
    )

    if notion_key:
        if st.button("🔍 Fetch My Notion Pages"):
            with st.spinner("Connecting to Notion..."):
                pages = get_notion_pages(notion_key)
                if pages:
                    st.session_state.notion_pages = pages
                    st.session_state.notion_key = notion_key
                    st.success(f"Found {len(pages)} pages!")
                else:
                    st.error("No pages found or invalid API key.")

    if "notion_pages" in st.session_state and st.session_state.notion_pages:
        st.markdown("---")
        st.subheader("Select a Page to Index")
        page_titles = [p["title"] for p in st.session_state.notion_pages]
        selected_title = st.selectbox("Choose page", page_titles)

        if st.button("📥 Index Selected Page", use_container_width=True):
            selected_page = next(p for p in st.session_state.notion_pages if p["title"] == selected_title)
            with st.spinner(f"Fetching and indexing {selected_title}..."):
                content = get_page_content(st.session_state.notion_key, selected_page["id"])
                if content:
                    add_document_to_index(user_id, content, selected_title, "notion")
                    save_note_to_db(user_id, selected_title, "notion", content)
                    st.success(f"✅ {selected_title} indexed successfully!")
                else:
                    st.error("Could not fetch page content. Make sure your integration has access to this page.")

    # show notion notes
    st.markdown("---")
    st.subheader("📁 Indexed Notion Pages")
    notes = get_notes(user_id)
    notion_notes = [n for n in notes if n["source"] == "notion"]

    if not notion_notes:
        st.info("No Notion pages indexed yet.")
    else:
        for note in notion_notes:
            st.markdown(f"🔗 **{note['file_name']}** — Indexed: {note['uploaded_at'][:10]}")

# ── TAB 3: Ask Question ──
with tab3:
    st.subheader("❓ Ask from Your Notes")

    notes = get_notes(user_id)
    if not notes:
        st.warning("No notes uploaded yet. Upload a PDF or connect Notion first.")
    else:
        st.success(f"You have {len(notes)} indexed document(s). Ask anything!")

        if "qa_history" not in st.session_state:
            st.session_state.qa_history = []

        # show history
        for qa in st.session_state.qa_history:
            with st.chat_message("user"):
                st.markdown(qa["question"])
            with st.chat_message("assistant"):
                st.markdown(qa["answer"])

        # input
        question = st.chat_input("Ask a question from your notes...")
        if question:
            with st.chat_message("user"):
                st.markdown(question)
            with st.chat_message("assistant"):
                with st.spinner("Searching your notes..."):
                    answer = answer_from_notes(user_id, question)
                    st.markdown(answer)
            st.session_state.qa_history.append({
                "question": question,
                "answer": answer
            })

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
    if st.button("🗓️ Planner"):
        st.switch_page("pages/planner.py")
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.switch_page("app.py")