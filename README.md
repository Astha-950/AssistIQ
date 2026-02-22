# 🧠 AssistIQ — AI Powered Personal Productivity Assistant

AssistIQ is an intelligent personal productivity assistant built for students preparing for jobs. It understands natural language, automatically manages your tasks and struggles, generates personalized daily plans, and answers questions from your own notes using RAG (Retrieval Augmented Generation).

---

## ✨ Features

- **💬 Natural Language Chat** — Just talk to your assistant. It automatically extracts tasks, struggles, and updates from your conversation — no manual form filling needed.

- **✅ Smart Task Manager** — Add tasks by just telling the assistant. Tracks pending, overdue, and completed tasks. Incomplete tasks automatically roll over to the next day.

- **💪 Struggle Tracker** — Tell the assistant what topics you are struggling with. It tracks your confidence score (1-10) and automatically flags topics when you improve.

- **🗓️ Personalized Daily Planner** — Generates a realistic day plan based on your pending tasks, overdue items, and weak topics. Plan persists all day and resets automatically next morning.

- **📚 Notes + RAG** — Upload your PDF notes or connect Notion pages. Ask questions and get answers grounded in your own content. Falls back to general knowledge if answer not found in notes.

- **🔥 Streak Tracking** — Tracks your daily usage streak to keep you motivated and consistent.

- **⚡ Smart Dashboard** — Greets you differently based on time of day. Reminds you to plan if you haven't, shows streak, pending tasks, and active struggles at a glance.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend + Backend | Streamlit |
| LLM | Groq (LLaMA 3.3 70B) |
| RAG Framework | LlamaIndex |
| Vector Database | ChromaDB |
| Embeddings | HuggingFace (BAAI/bge-small-en-v1.5) |
| Database + Auth | Supabase (PostgreSQL) |
| PDF Parsing | pdfplumber |
| Notion Integration | Notion API |
| CI/CD | GitHub Actions + Streamlit Cloud |

---

## 📁 Project Structure

```
AssistIQ/
├── app.py                  # Main entry point, login/signup
├── pages/
│   ├── dashboard.py        # Smart dashboard with streak
│   ├── chat.py             # Main AI chat interface
│   ├── tasks.py            # Task manager
│   ├── struggles.py        # Struggle tracker
│   ├── planner.py          # Daily planner
│   └── notes.py            # PDF upload + Notion + RAG
├── core/
│   ├── rag.py              # LlamaIndex + ChromaDB logic
│   ├── notion.py           # Notion API integration
│   └── rollover.py         # Incomplete task rollover logic
├── .github/
│   └── workflows/
│       └── ci.yml          # GitHub Actions CI pipeline
├── vector_store/           # ChromaDB persistent storage
├── .env                    # API keys (not committed)
└── requirements.txt
```

---

## ⚙️ Setup and Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/AssistIQ.git
cd AssistIQ
```

### 2. Create Virtual Environment
```bash
py -3.11 -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Mac/Linux
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Environment Variables
Create a `.env` file in root directory:
```
GROQ_API_KEY=your_groq_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
NOTION_API_KEY=your_notion_integration_key
```

### 5. Setup Supabase
Create the following tables in Supabase SQL Editor:

```sql
create table users (
  id uuid references auth.users primary key,
  name text,
  email text,
  current_streak int default 0,
  last_active_date date,
  plan_generated_today boolean default false,
  todays_plan text,
  plan_date date,
  created_at timestamp default now()
);

create table tasks (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references users(id),
  title text,
  deadline date,
  scheduled_date date,
  priority text default 'medium',
  status text default 'pending',
  completed_at timestamp,
  rollover_count int default 0,
  created_at timestamp default now()
);

create table struggles (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references users(id),
  topic text,
  confidence_score int default 2,
  status text default 'active',
  rollover_count int default 0,
  added_at timestamp default now(),
  resolved_at timestamp
);

create table notes (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references users(id),
  file_name text,
  source text,
  content text,
  uploaded_at timestamp default now()
);
```

### 6. Run the App
```bash
streamlit run app.py
```

---

## 🔑 Getting API Keys

| Service | Link |
|---|---|
| Groq (Free) | https://console.groq.com |
| Supabase (Free) | https://supabase.com |
| Notion API | https://www.notion.so/my-integrations |

---

## 🚀 CI/CD Pipeline

This project uses **GitHub Actions** for continuous integration:
- Automatically triggered on every push to `main` branch
- Sets up Python 3.11 environment
- Installs all dependencies
- Runs syntax checks on all Python files

Continuous deployment is handled by **Streamlit Cloud** — every push to `main` automatically redeploys the app.

---
 
 

## 🙋 Author

Built by **Astha Chaurasia**

---

## 📄 License

MIT License — feel free to use and modify.
