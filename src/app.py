"""app.py - Streamlit interface only; the logic lives in db.py, qa.py and llm.py.

Run with:  python -m streamlit run src/app.py
"""

import os

from dotenv import load_dotenv

load_dotenv()  # reads .env into environment variables (must run before importing llm)

import streamlit as st

import db
import embedding
import llm
import qa
import student_feedback

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
        /* Keep the selected value in the sidebar dropdown readable */
        section[data-testid="stSidebar"] div[data-baseweb="select"] * {
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

        /* Tabs: teal accent */
        .stTabs [aria-selected="true"] {
            color: #04656a;
        }
        .stTabs [data-baseweb="tab-highlight"] {
            background-color: #04656a;
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

# --- Fail fast if the API key isn't configured ---
if not os.getenv("GEMINI_API_KEY"):
    st.error("GEMINI_API_KEY is not set. Add it to your .env file before running the app.")
    st.stop()


# --- helpers ---
def show(value):
    """Display a value, or a clear message if the brief didn't state it."""
    return "Not stated in the brief" if value in (None, "", []) else str(value)


def date_or_raw(date_value, raw_value):
    """Prefer the exact wording from the brief, fall back to the parsed date."""
    return raw_value or date_value


@st.cache_data(ttl=60)
def load_assessments():
    return db.list_assessments()


@st.cache_data(ttl=60)
def load_full(assessment_id):
    return db.get_full_assessment(assessment_id)


@st.cache_resource(show_spinner="Loading the local embedding model and search index...")
def get_store():
    store = embedding.SimpleVectorStore()
    store.ensure_index()
    return store


# --- Load assessments from MySQL ---
assessments: list = []
try:
    assessments = load_assessments()
except Exception as e:
    st.error(
        "Couldn't connect to the database. Check that MySQL is running and "
        "that MYSQL_PASSWORD is set in your .env file."
    )
    st.exception(e)
    st.stop()

if not assessments:
    st.warning("No assessments found. Run the ingestion notebook to add some briefs.")
    st.stop()

labels = {
    a["id"]: f"{a['module_code'] or 'Unknown code'} - {a['module_title'] or a['source_file']}"
    for a in assessments
}

# --- Sidebar: Configuration ---
st.sidebar.markdown("### ⚙️ Configuration")
assessment_id = st.sidebar.selectbox(
    "Choose your assessment",
    options=list(labels.keys()),
    format_func=lambda i: labels[i],
)
if assessment_id is None:
    st.stop()
st.sidebar.divider()
st.sidebar.caption("🎓 Student mode: questions about your brief and feedback on your draft.")

use_retrieval = st.sidebar.checkbox(
    "Use retrieval (semantic search)",
    value=True,
    help="On: the long text sections are searched and only the relevant parts are sent. "
    "Off: the whole brief is sent (the baseline).",
)
store = None
if use_retrieval:
    try:
        store = get_store()
    except Exception as e:
        st.sidebar.error(f"Search index unavailable, using the baseline instead: {e}")
if store is not None and st.sidebar.button("🔄 Rebuild search index"):
    store.ensure_index(force=True)
    st.sidebar.success("Search index rebuilt.")

data = load_full(assessment_id)
facts = data["facts"]

st.subheader(labels[assessment_id])

chat_tab, feedback_tab, details_tab = st.tabs(
    ["💬 Ask a question", "📝 Draft feedback", "📋 Brief details"]
)

# --- Chat ---
SUGGESTIONS = [
    "When is this assessment due?",
    "What are the marking criteria?",
    "Am I allowed to use AI?",
    "What should I check before submitting?",
]

with chat_tab:
    chat_key = f"chat_{assessment_id}"  # a separate conversation per assessment
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []
    messages = st.session_state[chat_key]

    # Greeting and quick suggestion chips (only before the conversation starts)
    clicked_suggestion = None
    if not messages:
        with st.chat_message("assistant", avatar="📚"):
            st.markdown(
                "Hello! I am your assessment assistant. Ask me anything about "
                f"**{labels[assessment_id]}**."
            )
        chip_cols = st.columns(len(SUGGESTIONS))
        for i, (col, text) in enumerate(zip(chip_cols, SUGGESTIONS)):
            with col:
                if st.button(text, use_container_width=True, key=f"chip_{assessment_id}_{i}"):
                    clicked_suggestion = text

    # Display prior chat history
    for msg in messages:
        avatar = "📚" if msg["role"] == "assistant" else "🧑"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    # Chat input handling
    user_prompt = st.chat_input("Ask a question about this assessment...") or clicked_suggestion

    if user_prompt:
        history = list(messages)  # earlier turns only

        with st.chat_message("user", avatar="🧑"):
            st.markdown(user_prompt)

        with st.chat_message("assistant", avatar="📚"):
            answer, chunks = None, []
            with st.spinner("Reading the brief and generating..."):
                try:
                    answer, chunks = qa.answer_question(
                        user_prompt, assessment_id, history, store=store
                    )
                except llm.LLMUnavailable:
                    answer = None
                    st.warning(
                        "⚠️ **Service Notice:** the AI service is busy right now. "
                        "Please try again in a minute. The 'Brief details' tab still works."
                    )
                except Exception as e:
                    answer = None
                    st.error(f"Something went wrong: {e}")

            if answer:
                st.markdown(answer)
                if store is not None:
                    with st.expander("🔍 View retrieved context chunks (RAG)"):
                        st.caption(
                            "Facts, criteria, learning outcomes and the checklist come directly "
                            "from the database. These long-text sections were retrieved by search:"
                        )
                        if chunks:
                            for idx, c in enumerate(chunks, 1):
                                section = c["field"].replace("_", " ").capitalize()
                                st.write(f"**[{idx}] {section}** (Score: {c['similarity_score']})")
                                st.caption(c["content"][:250] + ("..." if len(c["content"]) > 250 else ""))
                        else:
                            st.caption("No long-text sections were found for this assessment.")
                else:
                    with st.expander("🔍 View the brief data used (baseline)"):
                        st.code(qa.format_context(data), language=None)
                messages.append({"role": "user", "content": user_prompt})
                messages.append({"role": "assistant", "content": answer})

# --- Draft feedback ---
with feedback_tab:
    st.markdown(
        "Paste your draft or upload it, and get feedback against this assessment's "
        "marking criteria **before** you submit."
    )
    st.caption(
        "Your draft is sent to the AI service to generate the feedback. It is not "
        "saved by this app. The feedback is automated and your lecturer's marking may differ."
    )

    uploaded = st.file_uploader(
        "Upload your draft (optional)",
        type=["pdf", "docx", "txt"],
        key=f"draft_file_{assessment_id}",
    )
    pasted = st.text_area(
        "Or paste your draft here",
        height=280,
        key=f"draft_text_{assessment_id}",
        placeholder="Paste the text of your draft...",
    )

    result_key = f"feedback_{assessment_id}"

    if st.button("Get feedback on my draft", key=f"feedback_btn_{assessment_id}"):
        draft_text = pasted
        if uploaded is not None:
            try:
                draft_text = student_feedback.read_draft_file(uploaded.name, uploaded.getvalue())
            except Exception as e:
                draft_text = ""
                st.error(f"Couldn't read that file: {e}")

        if draft_text.strip():
            with st.spinner("Comparing your draft with the marking criteria..."):
                try:
                    st.session_state[result_key] = student_feedback.give_feedback(
                        draft_text, assessment_id
                    )
                except ValueError as e:
                    st.session_state.pop(result_key, None)
                    st.warning(str(e))
                except llm.LLMUnavailable:
                    st.session_state.pop(result_key, None)
                    st.warning(
                        "⚠️ **Service Notice:** the AI service is busy right now. "
                        "Please try again in a minute."
                    )
                except Exception as e:
                    st.session_state.pop(result_key, None)
                    st.error(f"Something went wrong: {e}")
        elif uploaded is None:
            st.warning("Paste your draft or upload a file first.")

    result = st.session_state.get(result_key)
    if result:
        st.info(f"**Length check:** {result['word_check']}")
        with st.chat_message("assistant", avatar="📚"):
            st.markdown(result["feedback"])
        st.download_button(
            "Download feedback",
            data=result["feedback"],
            file_name="draft_feedback.md",
            mime="text/markdown",
            key=f"feedback_dl_{assessment_id}",
        )
        with st.expander("🔍 View the brief data used for this feedback"):
            st.code(qa.format_context(data), language=None)

# --- Brief details (answered from SQL, no model) ---
with details_tab:
    st.markdown("**Quick answers**")
    quick = {
        "Deadline": lambda: date_or_raw(facts["deadline"], facts["deadline_raw"]),
        "Word count": lambda: facts["word_count"],
        "Weighting": lambda: f"{facts['weighting_percent']}%" if facts["weighting_percent"] is not None else None,
        "Feedback date": lambda: date_or_raw(facts["feedback_date"], facts["feedback_date_raw"]),
        "Submission format": lambda: facts["submission_format"],
    }

    cols = st.columns(len(quick))
    for col, (label, getter) in zip(cols, quick.items()):
        if col.button(label, use_container_width=True, key=f"quick_{label}"):
            st.info(f"**{label}:** {show(getter())}")

    with st.expander("All key facts"):
        for key, value in facts.items():
            if key != "id":
                st.write(f"**{key.replace('_', ' ').capitalize()}:** {show(value)}")

    with st.expander("Learning outcomes"):
        outcomes = data["learning_outcomes"]
        if outcomes:
            for item in outcomes:
                st.write(f"- {item}")
        else:
            st.write(show(None))

    with st.expander("Marking criteria and grade bands"):
        if data["criteria"]:
            for c in data["criteria"]:
                weight = f" ({c['weighting_percent']}%)" if c["weighting_percent"] is not None else ""
                st.markdown(f"**{show(c['name'])}**{weight}")
                if c["description"]:
                    st.write(c["description"])
                for band in c["grade_bands"]:
                    st.write(f"- *{show(band['band_name'])}*: {show(band['descriptor'])}")
        else:
            st.write(show(None))

    with st.expander("Submission checklist"):
        checklist = data["submission_checklist"]
        if checklist:
            for item in checklist:
                st.write(f"- {item}")
        else:
            st.write(show(None))

    for field, text in data["text"].items():
        with st.expander(field.replace("_", " ").capitalize()):
            st.write(text)