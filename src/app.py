#%%
from pathlib import Path
from pdf_exporter import markdown_to_pdf
import os
import time
from dotenv import load_dotenv
from embedder import SimpleVectorStore
from google import genai
import streamlit as st
from brief_generator import LecturerBriefGenerator
from student_feedback import StudentFeedbackEngine


load_dotenv()  # reads .env into environment variables


#%%
# --- Page Setup ---
st.set_page_config(
    page_title="Academic RAG Prototype", page_icon="📚", layout="wide"
)

# --- Custom Styling (University-style teal accent, card look) ---
st.markdown(
    """
    <style>
        /* Overall app background */
        .stApp {
            background-color: #f7f9fa;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #04353a;
        }
        section[data-testid="stSidebar"] * {
            color: #f0f4f4 !important;
        }
        section[data-testid="stSidebar"] input {
            color: #111111 !important;
        }

        /* Header bar */
        .app-header {
            background-color: #04353a;
            padding: 1.1rem 1.5rem;
            border-radius: 12px;
            margin-bottom: 1.2rem;
        }
        .app-header h1 {
            color: #ffffff;
            font-size: 1.4rem;
            margin: 0;
        }
        .app-header p {
            color: #cfe3e1;
            margin: 0.2rem 0 0 0;
            font-size: 0.9rem;
        }

        /* Chat bubbles */
        div[data-testid="stChatMessage"] {
            background-color: #ffffff;
            border-radius: 14px;
            padding: 0.6rem 0.9rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            margin-bottom: 0.4rem;
        }

        /* Expander (retrieved chunks) */
        div[data-testid="stExpander"] {
            background-color: #ffffff;
            border: 1px solid #e2e8e8;
            border-radius: 10px;
        }

        /* Buttons */
        .stButton button, .stDownloadButton button {
            background-color: #04656a;
            color: white;
            border-radius: 8px;
            border: none;
        }
        .stButton button:hover, .stDownloadButton button:hover {
            background-color: #03494d;
            color: white;
        }

        /* Chat input box */
        .stChatInput {
            border-radius: 10px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Header ---
st.markdown(
    """
    <div class="app-header">
        <h1>📚 Academic Brief &amp; Feedback Assistant</h1>
        <p>Grounded in your module repository — assessment briefs, rubrics and learning outcomes</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Initialize RAG System (Cached so it loads once) ---
@st.cache_resource
def init_rag_system():
    store = SimpleVectorStore()
    store.load_index()
    return store, LecturerBriefGenerator(store), StudentFeedbackEngine(store)

vector_store, brief_gen, feedback_engine = init_rag_system()

# Function to be used  to handle API calls robustly
def generate_with_retry(client, prompt, primary_model="gemini-1.5-flash", max_retries=3):
    """Retries API calls and cascades through active supported Gemini models."""
    # List of active, standard Gemini models
    models_to_try = [primary_model, "gemini-2.0-flash", "gemini-1.5-pro"]
    
    for model_name in models_to_try:
        for attempt in range(1, max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                if response.text is None:
                   raise ValueError(
                        f"{model_name} returned an empty response (no text)."
                    )
                return response.text
            except Exception as e:
                err_msg = str(e)
                # If model is not found, jump directly to the next model in the list
                if "404" in err_msg or "NOT_FOUND" in err_msg:
                    print(f"[Notice] Model '{model_name}' not available. Trying next model...")
                    break
                # Handle temporary traffic spikes
                elif "503" in err_msg or "UNAVAILABLE" in err_msg:
                    print(f"[Notice] {model_name} busy (Attempt {attempt}/{max_retries}). Retrying in 2s...")
                    time.sleep(2 * attempt)
                else:
                    raise e
                    
    raise Exception("Gemini API is currently overloaded across all model tiers. Please wait a minute and try again.")

# --- Sidebar: Role & Model Configuration ---
st.sidebar.markdown("### ⚙️ Configuration")
user_role = st.sidebar.radio(
    "Select your role:",
    ["👨‍🏫 Lecturer (Brief Generator)", "🎓 Student (Draft Feedback & Q&A)"],
)

st.sidebar.divider()

# --- Fail fast if the API key isn't configured ---
# Catches a missing/misnamed .env, a load_dotenv() ordering issue, or
# running the app somewhere the key was never set — with a clear message
# at startup instead of an UnboundLocalError deep inside the chat handler.
api_key = os.getenv("GEMINI_API_KEY", "")
if not api_key:
    st.error("GEMINI_API_KEY is not set. Add it to your .env file before running the app.")
    st.stop()

# --- Chat History State ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hello! I am your RAG Assistant. How can I help you today?",
        }
    ]

# --- Quick suggestion chips (only before the conversation starts) ---
if len(st.session_state.messages) == 1:
    st.write("")
    chip_cols = st.columns(4)
    suggestions = [
        "What are the learning outcomes for this module?",
        "What does the assessment brief require?",
        "Show me an example of a past assignment",
        "Can I submit my work for checking?",
    ]
    clicked_suggestion = None
    for col, text in zip(chip_cols, suggestions):
        with col:
            if st.button(text, use_container_width=True):
                clicked_suggestion = text
else:
    clicked_suggestion = None

# Display prior chat history
for msg in st.session_state.messages:
    avatar = "📚" if msg["role"] == "assistant" else "🧑"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# --- Chat Input Handling ---
user_prompt = st.chat_input("Type your request or draft submission...") or clicked_suggestion

if user_prompt:

    # 1. Show User Message
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(user_prompt)

    # 2. Process according to selected Role
    with st.chat_message("assistant", avatar="📚"):
        with st.spinner("Retrieving document context and generating..."):

            if "Lecturer" in user_role:
                full_prompt, chunks = brief_gen.build_grounded_prompt(
                    user_prompt
                )
            else:
                full_prompt, chunks = feedback_engine.build_feedback_prompt(
                    user_prompt
                )

            # Show retrieved citations in an expander
            with st.expander("🔍 View retrieved context chunks (RAG)"):
                for idx, c in enumerate(chunks, 1):
                    st.write(
                        f"**[{idx}] {c['source_file']}** (Score: {c['similarity_score']})"
                    )
                    st.caption(c["content"][:250] + "...")

            # 3. Call LLM for final grounded response
            # api_key is guaranteed set at this point (we st.stop() above if not),
            # so this always runs and `answer` is always assigned.
            try:
                client = genai.Client(api_key=api_key)
                answer = generate_with_retry(client, full_prompt)
            except Exception as e:
                answer = f"⚠️ **Service Notice:** {str(e)}"
                st.markdown(answer)

            if "Lecturer" in user_role:
                pdf_filename = Path("generated_brief.pdf")
                markdown_to_pdf(answer, pdf_filename)

                with open(pdf_filename, "rb") as pdf_file:
                    st.download_button(
                        label="📄 Download Assessment Brief as PDF",
                        data=pdf_file,
                        file_name="Assessment_Brief_2026.pdf",
                        mime="application/pdf",
                    )

            st.session_state.messages.append(
                {"role": "assistant", "content": answer}
            )






