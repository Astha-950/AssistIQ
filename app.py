import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

st.set_page_config(
    page_title="AssistIQ",
    page_icon="🧠",
    layout="centered"
)

def login(email, password):
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        return response.user, None
    except Exception as e:
        return None, str(e)

def signup(name, email, password):
    try:
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        user = response.user
        # save user in users table
        supabase.table("users").insert({
            "id": user.id,
            "name": name,
            "email": email
        }).execute()
        return user, None
    except Exception as e:
        return None, str(e)

# if already logged in go to dashboard
if "user" in st.session_state and st.session_state.user:
    st.switch_page("pages/dashboard.py")

st.title("🧠 AssistIQ")
st.subheader("Your Personal Productivity Assistant")

tab1, tab2 = st.tabs(["Login", "Sign Up"])

with tab1:
    st.markdown("### Welcome Back!")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_pass")
    
    if st.button("Login", use_container_width=True):
        if email and password:
            user, error = login(email, password)
            if user:
                st.session_state.user = user
                st.success("Logged in successfully!")
                st.switch_page("pages/dashboard.py")
            else:
                st.error(f"Login failed: {error}")
        else:
            st.warning("Please fill all fields")

with tab2:
    st.markdown("### Create Account")
    name = st.text_input("Full Name", key="signup_name")
    email2 = st.text_input("Email", key="signup_email")
    password2 = st.text_input("Password", type="password", key="signup_pass")
    
    if st.button("Sign Up", use_container_width=True):
        if name and email2 and password2:
            user, error = signup(name, email2, password2)
            if user:
                st.success("Account created! Please login now.")
            else:
                st.error(f"Signup failed: {error}")
        else:
            st.warning("Please fill all fields")