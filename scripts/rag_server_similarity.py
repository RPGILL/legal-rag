# scripts/rag_server_similarity.py its a file name 

import os    # lets the script read environment setting
import json    # the script read and write json dat
import re     # script search text with pattern
from pathlib import Path    # tscript work with file and folder pat
from datetime import datetime, timezone   #  get date and time in ut
from typing import List, Set, Dict, Any, Tuple    # these are type hints to describe data typ

from fastapi import FastAPI, HTTPException    # imports fastapi and http error suppo
from fastapi.middleware.cors import CORSMiddleware   # s imports cors support so other apps can call this ap
from pydantic import BaseModel    #  imports pydantic models for request and response dat

from langchain_community.embeddings import HuggingFaceEmbeddings   #  imports the embedding model too
from langchain_community.vectorstores import FAISS   # imports the faiss vector store too

from openai import OpenAI    # s imports the openai clien
from openai import AuthenticationError, RateLimitError, APIConnectionError, APIStatusError   # these import common openai error


# CONFIG stores the main settings 

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")    # this gets the openai api key from the environme
if not OPENAI_API_KEY:      # checks if the api key is missin
    raise ValueError("Set OPENAI_API_KEY in environment (OPENAI_API_KEY)")     # stops the script if the api key is missin

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"    # is the embedding model nam
STORE_DIR = "data/faiss_langchain"    #  is the folder where the faiss index is save
OPENAI_MODEL = "gpt-4.1-mini"    # is the openai model nam

# Logging settingd for loggings
LOG_DIR = Path("logs")    # this is the folder for log file
QUERY_LOG = LOG_DIR / "queries_similarity.jsonl"  # optional separate log file  is the log file path for the similarity serve

#  Disclaimer enforcement next line to disclaimer 
REQUIRED_DISCLAIMER_LINE = "Information only (not legal advice)."   # is the exact disclaimer line the answer must start wit
DISCLAIMER_SECOND_LINE = (
    "This assistant provides general information about UK employment law and does not replace advice "
    "from a qualified solicitor, ACAS, or Citizens Advice."
)   # this is the second disclaimer lin


#  INIT APP starts fast api app and stuff

app = FastAPI(title="Legal RAG (Similarity-only Retrieval)")    # creates the fastapi app with a titl

app.add_middleware(    # this adds cors middlewa
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_credentials=True,     # this allows all websites to call the ap nd  this allows credential
    allow_methods=["*"],      # allows all http method
    allow_headers=["*"],      # this allows all header
)


#  INIT MODELS nd  VECTOR STORE loads the model faiiss

embedder = HuggingFaceEmbeddings(model_name=EMBED_MODEL)     #  tells faiss where the saved store i
vectorstore = FAISS.load_local(
    STORE_DIR,
    embedder,      #  gives faiss the embedding mode
    allow_dangerous_deserialization=True      # allows faiss to load saved local dat
)

client = OpenAI(api_key=OPENAI_API_KEY)    #  creates the openai client using the api ke


#  Pydantic MODELS makes request and response model 

class Query(BaseModel):      #  makes the model for incoming question dat
    question: str     # says the request must have a question text fiel


class Source(BaseModel):       # t makes the model for one source ite
    title: str | None = None     #  source can have a title or no titl
    url: str | None = None      # this source can have a url or no ur


class AnswerResponse(BaseModel):     #  makes the model for the api respon
    answer: str      #  the response has answer tex
    sources: List[Source]       #  the response has a list of source


# Topic helpers helps with topic guesssing 

PAY_KEYWORDS = {     # these are words linked to pay question
    "pay", "paid", "wage", "wages", "salary", "underpaid", "unpaid",
    "deduction", "deductions", "minimum wage", "national minimum wage",
    "national living wage", "overtime", "payslip", "final pay", "commission", "bonus"
}

HOLIDAY_KEYWORDS = {      # same again 
    "holiday", "annual leave", "leave", "holiday pay", "entitlement", "accrue", "accrued",
    "bank holiday", "rolled-up"
}

DISMISSAL_KEYWORDS = {       # same again 
    "dismiss", "dismissal", "sacked", "fired", "notice", "redundancy", "unfair dismissal",
    "constructive dismissal", "appeal", "disciplinary"
}

DISCRIMINATION_KEYWORDS = {     # same again 
    "discrimination", "harassment", "victimisation", "equality act", "protected characteristic",
    "race", "religion", "sex", "disability", "pregnancy", "maternity"
}


def detect_topic(q: str) -> str:       # this makes a function to guess the question topi
    text = q.lower()        #  changes the question to lower cas

    pay_hits = sum(1 for k in PAY_KEYWORDS if k in text)      #  counts how many pay words are in the questio
    holiday_hits = sum(1 for k in HOLIDAY_KEYWORDS if k in text)       # ts how many holiday words are in the questio
    dismissal_hits = sum(1 for k in DISMISSAL_KEYWORDS if k in text)     # counts how many dismissal words are in the questio
    discrim_hits = sum(1 for k in DISCRIMINATION_KEYWORDS if k in text)    # this counts how many discrimination words are in the questio

    scores = [       # this stores the pay scor
        ("pay", pay_hits),      # this stores the holiday scor
        ("holiday", holiday_hits),     # same again 
        ("dismissal", dismissal_hits),    # same again 
        ("discrimination", discrim_hits),     # same again 
    ]

    best_topic, best_score = max(scores, key=lambda x: x[1])       #  picks the topic with the biggest scor
    return best_topic if best_score > 0 else "general"      # returns the best topic if there was a matc


def question_mentions_holiday(q: str) -> bool:       # this makes a function to check if the question mentions holida
    t = q.lower()      # s changes the question to lower ca
    return any(k in t for k in HOLIDAY_KEYWORDS)     #  returns true if any holiday word is foun


def doc_blob(doc) -> str:      #  one big lower-case text from a documen
    url = (doc.metadata.get("url") or "").lower()     # gets the document url and changes it to lower cas
    title = (doc.metadata.get("title") or "").lower()     # the document title and changes it to lower cas
    content = (doc.page_content or "").lower()     # ts the document text and changes it to lower cas
    return f"{url} {title} {content}"      #  joins url, title, and content into one text bloc


def doc_matches_topic(doc, topic: str, q_has_holiday: bool) -> bool:       #  makes a function to check if one document matches the topi
    blob = doc_blob(doc)       # tbuilds one big text block from the documen

    # Prevent PAY-only questions from pulling HOLIDAY docs just because of the word pay
    if topic == "pay" and not q_has_holiday:     # checks if the topic is pay and the question did not mention holida
        if "holiday" in blob or "annual leave" in blob:     # checks if the document looks like a holiday documen
            return False       # says do not use this documen

    if topic == "pay":      # this checks if the topic is pa
        return any(k in blob for k in ["wage", "wages", "minimum wage", "living wage", "deduction", "payslip", "pay"])
    if topic == "holiday":  # same again 
        return any(k in blob for k in ["holiday", "annual leave", "holiday pay", "entitlement", "leave"])
    if topic == "dismissal":       # same again
        return any(k in blob for k in ["dismiss", "dismissal", "notice", "unfair dismissal", "constructive", "redundancy"])
    if topic == "discrimination":     # same again
        return any(k in blob for k in ["discrimination", "equality act", "harassment", "victimisation", "protected characteristic"])
            
    return True      # this returns true if any pay word is found in the docume


#  Prompt builder builds the prompt for api

def build_prompt(question: str, docs) -> str:         # this makes a function to build the full prom
    context_parts = []              # this empty list will store the source bloc
    for i, d in enumerate(docs):        # this empty list will store the source bloc
        title = d.metadata.get("title") or f"Source {i+1}"        # this empty list will store the source bloc
        url = d.metadata.get("url") or "Unknown URL"        # this empty list will store the source bloc
        text = d.page_content        # this empty list will store the source bloc
        context_parts.append(         # this empty list will store the source bloc
            f"[Source {i+1}: {title}]\nURL: {url}\nContent:\n{text}\n"         # this empty list will store the source bloc
        )

    context_str = "\n\n".join(context_parts)        # this empty list will store the source bloc

    return f"""
You are an assistant providing INFORMATION ONLY about UK employment law (NOT legal advice).
Topics include:
- unfair dismissal
- discrimination (Equality Act 2010)
- pay issues (unpaid wages / unlawful deductions / minimum wage)
- holiday entitlement and holiday pay

CRITICAL RULES:     
- You MUST start your answer with this exact line:
  {REQUIRED_DISCLAIMER_LINE}
- Use ONLY the sources below.
- If the sources do not contain enough information to answer safely, say:
  "I don't know from these sources — please consult a qualified solicitor, ACAS, or Citizens Advice."

OUTPUT FORMAT (follow exactly):
1) Start with: {REQUIRED_DISCLAIMER_LINE}
2) 1–3 short paragraphs answering in plain English.
3) Step-by-step suggestion (Step 1… Step 2…) if appropriate.
4) End with:
Sources used:
- <url>
- <url>

----------------- SOURCES -----------------
{context_str}
-------------------------------------------

User question: {question}
""".strip()


#  Disclaimer enforcement 

def ensure_disclaimer(answer_text: str) -> str:
    if not answer_text:           # this empty list will store the source bloc
        return f"{REQUIRED_DISCLAIMER_LINE}\n{DISCLAIMER_SECOND_LINE}\n"        # this empty list will store the source bloc

    text = answer_text.strip()          # this empty list will store the source bloc

    if text.startswith(REQUIRED_DISCLAIMER_LINE):         # this empty list will store the source bloc
        return text

    text = re.sub(r"(?im)^\s*Information only \(not legal advice\)\.\s*$\n?", "", text).strip()
    return f"{REQUIRED_DISCLAIMER_LINE}\n{DISCLAIMER_SECOND_LINE}\n\n{text}".strip()       # this empty list will store the source bloc


# Sources parsing + normalization 

_URL_RE = re.compile(r"https?://[^\s)>\]]+", re.IGNORECASE)     # this pattern finds urls in tex

def _dedupe_preserve_order(urls: List[str]) -> List[str]:     # this makes a function to remove duplicate urls but keep the same orde
    seen: Set[str] = set()      # this empty set remembers urls already adde
    out: List[str] = []      # this empty list stores the final url
    for u in urls:        # this goes through each ur
        u2 = u.strip()       # this goes through each ur
        if not u2:           # this goes through each ur
            continue        # this goes through each ur
        if u2 in seen:        # this goes through each ur
            continue        # if yes skip i
        seen.add(u2)         # this remembers the ur
        out.append(u2)      # this remembers the ur
    return out        # this remembers the ur


def extract_sources_section_urls(answer_text: str) -> List[str]:          # this function gets urls only from the Sources used sectio
    if not answer_text:       # checks if the answer is empt
        return []      # this returns an empty list if there is no answe

    m = re.search(r"(?im)^\s*Sources used\s*:\s*$", answer_text)      # this returns an empty list if there is no answe
    if not m:       # this returns an empty list if there is no answe
        return []         # this returns an empty list if there is no answe

    tail = answer_text[m.end():]        # this returns an empty list if there is no answe
    urls = _URL_RE.findall(tail)       # this returns an empty list if there is no answe
    return _dedupe_preserve_order(urls)       # this returns an empty list if there is no answe


def strip_existing_sources_section(answer_text: str) -> str:      # this returns an empty list if there is no answe
    if not answer_text:        # this checks if the answer is empt
        return ""      # this returns empty tex
    return re.sub(r"(?ims)\n?\s*Sources used\s*:\s*\n.*\Z", "", answer_text).rstrip()     # this removes the Sources used section from the end of the answe


def canonicalize_sources(answer_text: str, available_sources: List[Source]) -> Tuple[str, List[Source]]:
    url_to_source: Dict[str, Source] = {}      # this function makes the final clean sources bloc
    for s in available_sources:       #  empty dictionary will match urls to source object
        if s.url:        # goes through each available sourc
            url_to_source[s.url] = s         # this checks if the source has 

    used_urls = extract_sources_section_urls(answer_text)       # this checks if the source has 

    if used_urls:        # this checks if the source has 
        filtered_urls = [u for u in used_urls if u in url_to_source]        # this checks if the source has 
        sources_used = [url_to_source[u] for u in filtered_urls] if filtered_urls else available_sources
    else:
        sources_used = available_sources      # this checks if the source has 

    body = strip_existing_sources_section(answer_text).rstrip()       # this checks if the source has 
    lines = ["Sources used:"]        # this checks if the source has 
    for s in sources_used:        # this checks if the source has 
        if s.url:          # this checks if the source has 
            lines.append(f"- {s.url}")        # this checks if the source has 
    sources_block = "\n".join(lines)         # this checks if the source has 

    if body:        # this checks if the source has 
        new_answer = f"{body}\n\n{sources_block}"          # this checks if the source has 
    else:
        new_answer = sources_block       # this checks if the source has 

    return new_answer, sources_used        # this checks if the source has 


# Logging helpers 

def ensure_log_dir():       # this makes sure the log folder exist
    LOG_DIR.mkdir(parents=True, exist_ok=True)        # this creates the log folder if it does not already exis


def doc_to_log_dict(doc) -> Dict[str, Any]:        # this makes one simple log record for a documen
    return {
        "title": doc.metadata.get("title"),       # this saves the document title
        "url": doc.metadata.get("url"),        # this saves the document title
        "source_file": doc.metadata.get("source_file"),         # this saves the document title
        "chunk_start_word": doc.metadata.get("chunk_start_word"),       # this saves the document title
        "preview": (doc.page_content[:240] + "…") if doc.page_content and len(doc.page_content) > 240 else (doc.page_content or "")
    }


def write_query_log(record: Dict[str, Any]) -> None:      # this saves the document title
    ensure_log_dir()         # this saves the document title
    with QUERY_LOG.open("a", encoding="utf-8") as f:        # this saves the document title
        f.write(json.dumps(record, ensure_ascii=False) + "\n")        # this saves the document title


#  ROUTES 

@app.get("/")       # this saves the document title
def read_root():
    return {"status": "ok", "message": "Legal RAG Similarity-only API is running"}      # this saves the document title


@app.post("/ask", response_model=AnswerResponse)       # this saves the document title
def ask(query: Query):        # this saves the document title
    question = (query.question or "").strip()       # this saves the document title
    if not question:
        raise HTTPException(status_code=400, detail="Question must not be empty.")      # this saves the document title

    topic = detect_topic(question)
    q_has_holiday = question_mentions_holiday(question)       # this saves the document title

    #  ONLY CHANGE: similarity-only retrieval (no MMR, no try/except fallback)
    retrieval_method = "similarity_only"
    candidates = vectorstore.similarity_search(question, k=15)      # this saves the document title

    # 2) Prefer topic-matching docs
    topic_docs = [d for d in candidates if doc_matches_topic(d, topic, q_has_holiday)]      # this saves the document title

    #  Pick final docs top 4 but ONLY add more docs that match topic.
    docs = topic_docs[:4]      # this saves the document title

    if len(docs) < 4:         # this checks if there are fewer than 4 docume
        for d in candidates:      # this goes through all candidate documen
            if d in docs:       # this checks if the document is already chose
                continue      # this checks if the document is already chose
            if doc_matches_topic(d, topic, q_has_holiday):        # this checks if the document is already chose
                docs.append(d)        # this checks if the document is already chose
            if len(docs) >= 4:       # this checks if the document is already chose
                break      # this checks if the document is already chose

    prompt = build_prompt(question, docs)       # this checks if the document is already chose

    #  OpenAI call
    try:        # this tries to call openai safel
        completion = client.chat.completions.create(
            model=OPENAI_MODEL,          # this tries to call openai safel
            messages=[
                {"role": "system", "content": "You provide UK employment law information only (not legal advice)."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,       # this tries to call openai safel
        )
    except AuthenticationError:       # this runs if the api key is wron
        raise HTTPException(status_code=401, detail="OpenAI authentication failed. Check OPENAI_API_KEY.")
    except RateLimitError:       # this runs if the api key is wron
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
    except APIConnectionError:       # this runs if the api key is wron
        raise HTTPException(status_code=503, detail="Could not connect to OpenAI. Check your internet connection.")
    except APIStatusError as e:       # this runs if the api key is wron
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {str(e)}")
    except Exception as e:       # this runs if the api key is wron
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
           # this runs if the api key is wron
    answer_text = completion.choices[0].message.content or ""        # this runs if the api key is wron

    #  Ensure disclaimer is present and starts correctly
    answer_text = ensure_disclaimer(answer_text)

    # 5) Build source list (dedupe by URL)
    seen_urls: Set[str] = set()      # this empty set remembers urls already adde
    available_sources: List[Source] = []       # this empty list stores the final available sourc
    for d in docs:      # this empty list stores the final available sourc
        title = d.metadata.get("title")      # this empty list stores the final available sourc
        url = d.metadata.get("url")      # this empty list stores the final available sourc

        if url:      # this empty list stores the final available sourc
            if url in seen_urls:      # this empty list stores the final available sourc
                continue      # this empty list stores the final available sourc
            seen_urls.add(url)     # this empty list stores the final available sourc

        available_sources.append(Source(title=title, url=url))

    # Canonicalize sources: dedupe + rewrite "Sources used:" once
    answer_text, sources_used = canonicalize_sources(answer_text, available_sources)     # this empty list stores the final available sourc

    # 6) LOG the request + retrieval + response
    log_record = {        # this saves the current utc tim
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "question": question,       # this saves the questio
        "topic": topic,         # this saves the guessed topi
        "question_mentions_holiday": q_has_holiday,      # same again 
        "retrieval_method": retrieval_method,    # same again 
        "openai_model": OPENAI_MODEL,    # same again 
        "retrieved_docs": [doc_to_log_dict(d) for d in docs],     # same again 
        "returned_sources": [{"title": s.title, "url": s.url} for s in sources_used],    # same again 
        "answer": answer_text     # same again 
    }
    write_query_log(log_record)      # this writes the log record to the log fil

    return AnswerResponse(answer=answer_text, sources=sources_used)     # this returns the final answer and sources to the use
