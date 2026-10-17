import json
import re
from pathlib import Path

import streamlit as st
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).parent
QUESTIONS_FILE = ROOT / "data" / "processed" / "questions.json"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

st.set_page_config(page_title="AKTU PYQ Search", page_icon="📚", layout="wide")
st.title("📚 AKTU PYQ Search Engine")
st.caption("Find relevant previous-year questions by topic, subject, or year.")


@st.cache_resource
def load_model():
    return SentenceTransformer(MODEL_NAME)


@st.cache_data
def load_questions(path_string, modified_time):
    path = Path(path_string)
    with path.open("r", encoding="utf-8") as file:
        questions = json.load(file)

    if not isinstance(questions, list):
        raise ValueError("The index must contain a JSON list of question records.")
    if any(not isinstance(question, dict) for question in questions):
        raise ValueError("Every item in the index must be a question record.")
    return questions


@st.cache_data(show_spinner=False)
def encode_questions(texts):
    return load_model().encode(
        list(texts),
        normalize_embeddings=True,
        convert_to_numpy=True,
    )


if QUESTIONS_FILE.exists():
    try:
        questions = load_questions(
            str(QUESTIONS_FILE),
            QUESTIONS_FILE.stat().st_mtime,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        st.error(f"Could not load the question index: {exc}")
        st.stop()
else:
    questions = []

searchable_questions = [
    question
    for question in questions
    if isinstance(question.get("question"), str) and question["question"].strip()
]
blank_question_count = len(questions) - len(searchable_questions)
paper_count = len({q.get("source_file") for q in questions if q.get("source_file")})
subject_count = len({q.get("subject") for q in questions if q.get("subject")})
normalized_texts = [
    re.sub(r"\s+", " ", q["question"]).strip().casefold()
    for q in searchable_questions
]
duplicate_count = len(normalized_texts) - len(set(normalized_texts))

search_tab, quality_tab, overview_tab = st.tabs(
    ["Search questions", "Data quality", "Project overview"]
)

with st.sidebar:
    st.header("Search filters")
    if searchable_questions:
        subjects = sorted({q.get("subject", "Unknown") for q in searchable_questions})
        years = sorted(
            {str(q.get("year", "Unknown")) for q in searchable_questions},
            reverse=True,
        )
        chosen_subjects = st.multiselect("Subject", subjects, default=subjects)
        chosen_years = st.multiselect("Year", years, default=years)
        top_k = st.slider(
            "Number of results",
            min_value=1,
            max_value=min(20, len(searchable_questions)),
            value=min(5, len(searchable_questions)),
        )
    else:
        chosen_subjects = []
        chosen_years = []
        top_k = 0
        st.caption("Add and index PDFs to enable search filters.")
    st.caption(f"Searchable questions: {len(searchable_questions)}")

with search_tab:
    if not QUESTIONS_FILE.exists():
        st.info(
            "The search index has not been created yet. Add permitted question-paper "
            "PDFs to `data/papers/`, then run `python ingest_pdfs.py`."
        )
    elif not searchable_questions:
        st.warning(
            "The index contains no searchable question text. Check the PDFs and "
            "ingestion output, then run `python ingest_pdfs.py` again."
        )
    else:
        query = st.text_input(
            "Search question or topic",
            placeholder="e.g., Explain binary search tree insertion",
        )
        search_clicked = st.button("🔎 Search PYQs", type="primary")

        if search_clicked:
            if not query.strip():
                st.info("Enter a topic or question to search.")
            else:
                eligible = [
                    question
                    for question in searchable_questions
                    if question.get("subject", "Unknown") in chosen_subjects
                    and str(question.get("year", "Unknown")) in chosen_years
                ]
                if not eligible:
                    st.warning(
                        "No questions match these filters. Try selecting more "
                        "subjects or years."
                    )
                else:
                    texts = tuple(question["question"] for question in eligible)
                    with st.spinner("Finding the most relevant questions..."):
                        corpus_vectors = encode_questions(texts)
                        query_vector = load_model().encode(
                            [query],
                            normalize_embeddings=True,
                            convert_to_numpy=True,
                        )[0]
                        scores = corpus_vectors @ query_vector

                    ranked = sorted(
                        zip(scores, eligible),
                        key=lambda result: float(result[0]),
                        reverse=True,
                    )[:top_k]
                    st.subheader(f"Top {len(ranked)} results")
                    for rank, (score, item) in enumerate(ranked, start=1):
                        with st.container(border=True):
                            st.markdown(
                                f"**{rank}. {item['question'].strip()}**"
                            )
                            st.caption(
                                f"Subject: {item.get('subject', 'Unknown')}  |  "
                                f"Year: {item.get('year', 'Unknown')}  |  "
                                f"Paper: {item.get('paper', 'Unknown')}  |  "
                                f"Similarity: {float(score):.3f}"
                            )
                            if item.get("source_url"):
                                st.markdown(
                                    f"[Open source paper]({item['source_url']})"
                                )
                            elif item.get("source_file"):
                                st.caption(f"Source file: {item['source_file']}")
                            if item.get("page"):
                                st.caption(f"PDF page: {item['page']}")

with quality_tab:
    st.subheader("Question-bank profile")
    metric_columns = st.columns(4)
    metric_columns[0].metric("Indexed records", len(questions))
    metric_columns[1].metric("Searchable questions", len(searchable_questions))
    metric_columns[2].metric("Source papers", paper_count)
    metric_columns[3].metric("Subjects", subject_count)

    st.write(f"Blank or missing question text: **{blank_question_count}**")
    st.write(f"Exact duplicate question text: **{duplicate_count}**")

    if not QUESTIONS_FILE.exists():
        st.warning("No index exists yet, so there is no project data to profile.")
    elif not searchable_questions:
        st.warning("No usable question text was found in the index.")
    else:
        missing_source = sum(not q.get("source_file") for q in searchable_questions)
        missing_subject = sum(not q.get("subject") for q in searchable_questions)
        missing_year = sum(not q.get("year") for q in searchable_questions)
        st.write(f"Records without source-file attribution: **{missing_source}**")
        st.write(f"Records without a subject: **{missing_subject}**")
        st.write(f"Records without a year: **{missing_year}**")

    st.info(
        "Model performance is not reported yet. Precision@5 and Recall@5 require a "
        "small, manually relevance-labeled set of real search queries."
    )

with overview_tab:
    st.subheader("Project problem and approach")
    st.markdown(
        """
        **Problem statement:** AKTU students preparing for exams can struggle to find
        relevant questions across previous-year paper PDFs. This project uses
        sentence-embedding similarity to retrieve questions from permitted PDFs.

        **Intended measurable outcome:** evaluate whether relevant questions appear
        near the top of search results using Precision@5 and Recall@5 on a manually
        labeled query set. These metrics will be added only after real papers and
        relevance judgments are available.

        **Data source:** question-paper PDFs supplied by the project owner, with
        subject, semester, year, and source attribution recorded where available.
        """
    )
    st.markdown(
        """
        **Current workflow**
        1. Add permitted PDFs under `data/papers/`.
        2. Match each PDF to a row in `papers_metadata.csv`.
        3. Run `python ingest_pdfs.py` and inspect the extracted question records.
        4. Run `streamlit run app.py` and search the indexed questions.
        """
    )

st.divider()
st.caption(
    "Academic-use prototype. Similarity scores measure text similarity, "
    "not correctness or exam importance."
)
