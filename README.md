# Development of a Legal RAG (Retrieval-Augmented Generation) Assistant for UK Employment Law

An AI-powered Retrieval-Augmented Generation (RAG) system that provides **information only (not legal advice)** about UK employment law. The system combines OpenAI language models with a FAISS vector database to retrieve relevant legal guidance before generating grounded responses.

> **Disclaimer:** This application provides information only and is **not legal advice**.

---

## Features

- Retrieval-Augmented Generation (RAG)
- FAISS vector search
- OpenAI GPT integration
- FastAPI REST API
- Evaluation framework
- Baseline (LLM-only) comparison
- Citation and source tracking
- Hallucination evaluation
- Employment law document retrieval

---

## Project Structure

```
project/
│
├── corpus/                 # Source employment law documents
├── eval/                   # Evaluation outputs
│   ├── runs/
│   ├── results.jsonl
│   ├── summary.csv
│   └── summary_baseline.csv
│
├── eval_sets/
│   └── questions_v1.txt
│
├── index/
│   ├── faiss.index
│   └── metadata.pkl
│
├── scripts/
│   ├── rag_server.py
│   ├── evaluate_rag.py
│   ├── evaluate_baseline.py
│   ├── analyse_results.py
│   └── analyse_baseline.py
│
├── requirements.txt
└── README.md
```

---

## Technologies Used

- Python 3.11+
- OpenAI API
- LangChain
- FAISS
- FastAPI
- Pandas
- Uvicorn

---

## Installation

Clone the repository:

```bash
git clone https://github.com/yourusername/uk-employment-law-rag.git
cd uk-employment-law-rag
```

Create a virtual environment:

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file or set the environment variable:

```text
OPENAI_API_KEY=your_api_key_here
```

Optionally specify the model:

```text
OPENAI_MODEL=gpt-4.1-mini
```

---

## Running the API

Start the FastAPI server:

```bash
uvicorn scripts.rag_server:app --reload --port 8000
```

The API will be available at:

```
http://127.0.0.1:8000
```

Swagger documentation:

```
http://127.0.0.1:8000/docs
```

---

## Running the RAG Evaluation

```bash
python scripts/evaluate_rag.py
```

Analyse results:

```bash
python scripts/analyse_results.py
```

Outputs are saved in:

```
eval/
```

---

## Running the Baseline (LLM Only)

The baseline does **not** use retrieval.

Pipeline:

```
Question
    ↓
OpenAI GPT
    ↓
Answer
```

Run:

```bash
python scripts/evaluate_baseline.py
```

Analyse:

```bash
python scripts/analyse_baseline.py
```

Outputs:

```
eval/summary_baseline.csv
```

---

## Evaluation Metrics

The project evaluates:

- Response latency
- Citation presence
- Citation failures
- Hallucinated URLs
- Disclaimer compliance
- Retrieval effectiveness

These metrics allow comparison between:

- RAG system
- LLM-only baseline

---

## API Example

Request:

```json
POST /ask

{
    "question": "Can my employer dismiss me while I am off sick?"
}
```

Response:

```json
{
    "answer": "...",
    "sources": [
        "https://www.acas.org.uk/",
        "https://www.gov.uk/"
    ]
}
```

---

## Research Purpose

This project was developed as part of an Honours Individual Project investigating whether Retrieval-Augmented Generation (RAG) improves the reliability and transparency of AI-generated responses for UK employment law compared with a standard Large Language Model.

---

## Disclaimer

This software is intended **for educational and research purposes only**.

It does **not** provide legal advice. Users should consult qualified legal professionals, ACAS, or Citizens Advice for legal guidance.

---

