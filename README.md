# AKTU PYQ Search Engine

A student project that extracts text from AKTU previous-year question-paper PDFs and searches the questions using semantic similarity.

## Capstone problem statement

AKTU students preparing for exams can struggle to find relevant questions across previous-year paper PDFs. This project uses sentence-embedding similarity to retrieve questions from permitted PDFs, with subject and year filters.

The intended model-performance target is to measure **Precision@5** and **Recall@5** on a manually relevance-labeled set of real search queries. No relevance-labeled query set exists yet, so no performance scores are reported. Question-paper PDFs and the generated index are not included in this repository; add permitted PDFs locally before running ingestion.

## Build the project step by step

1. **Define the problem.** The target users are AKTU students; the task is finding relevant past-paper questions by topic or natural-language query.
2. **Collect and profile the data.** Add permitted, text-readable PDFs and metadata. Run the ingestion script, inspect `questions.json`, and use the app's **Data quality** tab to check record counts, missing fields, and duplicates.
3. **Evaluate the model.** Create a small set of realistic search queries and manually label which indexed questions are relevant. Calculate Precision@5 and Recall@5 before claiming the search is effective. This evaluation is not yet available because the project currently has no question-paper PDFs or labels.
4. **Test the interface.** Start the Streamlit app and verify search, filters, citations, and empty-data messages.
5. **Prepare the submission.** After gathering real evaluation results, write the two-page executive summary and five-slide presentation required by the reading guide. Explain limitations and next steps honestly.

Current local layout:

```text
app.py                    Streamlit search interface and data-quality profile
ingest_pdfs.py            PDF extraction and question-record generation
papers_metadata.csv       Metadata matched to PDF filenames
data/
  papers/                 Input PDFs (not included in the project)
  processed/              Generated question index
```

## Features

- Search by topic or natural-language question
- Semantic matching with Sentence-Transformers
- Filter results by subject and year
- Show source PDF, page number, and similarity score
- Local prototype; no API key required

## Requirements

- Python 3.10 or 3.11 recommended
- Internet connection for the first model download
- AKTU PYQ PDFs that you are permitted to use

## Setup on Windows (VS Code)

1. Install Python from https://www.python.org/downloads/ and select **Add Python to PATH** during installation.
2. Install VS Code from https://code.visualstudio.com/ and install the Microsoft Python extension.
3. Extract this project ZIP and open the `aktu_pyq_search_engine` folder in VS Code.
4. Open **Terminal → New Terminal**.
5. Create a virtual environment:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, try Command Prompt and run:
   `.\.venv\Scripts\activate.bat`

6. Install libraries:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

## Add question papers

1. Put PDF files in `data/papers/`.
2. Open `papers_metadata.csv` and add one row per PDF. The filename must exactly match the PDF name. Example:

   ```csv
   filename,subject,year,semester,paper,source_url
   KCS301_Nov_2024.pdf,Data Structures,2024,3,Data Structures End Semester Nov 2024,https://example.edu/paper.pdf
   ```

   Replace the example URL with the real source URL, or leave it blank. Do not use `https://example.edu` as a real source.
3. Run:

   ```powershell
   python ingest_pdfs.py
   ```

4. Open `data/processed/questions.json`. Check the extracted text. PDF layouts differ, so correct any badly split questions and re-run the parser if needed.

### Important: scanned PDFs

If a PDF is a scanned image, PyMuPDF may extract no text. Run OCR (for example, Tesseract) on those PDFs before indexing, or add OCR support to the parser. The starter parser does not include OCR.

## Start the app

```powershell
streamlit run app.py
```

A browser tab should open. Enter a topic or question and press **Search PYQs**.

## How it works

1. PyMuPDF extracts page text.
2. The parser separates text into searchable units.
3. Sentence-Transformers converts the query and question text into vectors.
4. Normalized vectors are compared using dot product, equivalent to cosine similarity.
5. Streamlit displays the highest-scoring results.

The first search downloads the embedding model, so it may take a few minutes. Question vectors are cached for repeated searches during the app session.

## Troubleshooting

- **No PDFs found:** confirm the PDFs are inside `data/papers/`.
- **No indexed questions:** run `python ingest_pdfs.py` and inspect the terminal output.
- **Bad question splits:** manually review `questions.json`; change `QUESTION_START` in `ingest_pdfs.py` to suit your paper layout.
- **Model download fails:** check your internet connection and try again.
- **Scanned paper:** OCR is needed; this starter only reads embedded text.
- **Installation error:** use Python 3.10/3.11 in a fresh virtual environment.

## Data and permissions

Prefer the university's official question-paper archive or materials shared by your college/library. Keep source links and attribution. Check the source site's terms and any copyright restrictions before redistributing PDFs. For a public demo, consider linking to source papers rather than republishing complete PDFs.

## Limitations and future improvements

- Parser may split some formats incorrectly.
- OCR is not built in.
- Similarity is not a measure of exam importance or answer correctness.
- For larger collections, cache embeddings and use FAISS or another vector index.
- Add course/branch filters, exact subject-code filters, duplicate detection, evaluation labels, and user feedback.
