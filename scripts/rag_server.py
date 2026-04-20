# scripts/rag_server.py its a file name 

import os      # lets the script read environment settin
import json     # script read and write json dat
import re     # t search text with patter
from pathlib import Path    # lets the script work with file and folder pat
from datetime import datetime, timezone    # the script get date and time in ut
from typing import List, Set, Dict, Any, Tuple    # these are type hints to describe data typ

from fastapi import FastAPI, HTTPException    # timports fastapi and http error suppo
from fastapi.middleware.cors import CORSMiddleware    # imports cors support so other apps can call this api
from pydantic import BaseModel    #  imports pydantic models for request and response dat

from langchain_community.embeddings import HuggingFaceEmbeddings    #  imports the embedding model too
from langchain_community.vectorstores import FAISS    #  imports the faiss vector store too

from openai import OpenAI   # this imports the openai clien
from openai import AuthenticationError, RateLimitError, APIConnectionError, APIStatusError   # t common openai error


# CONFIG 

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")     # this gets the openai api key from the environme
if not OPENAI_API_KEY:      #  checks if the api key is missin
    raise ValueError("Set OPENAI_API_KEY in environment (OPENAI_API_KEY)")     # stops the script if the api key is missin

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  #  is the embedding model nam
STORE_DIR = "data/faiss_langchain"    #  the folder where the faiss index is save
OPENAI_MODEL = "gpt-4.1-mini"    # this is the openai model nam

# Logging
LOG_DIR = Path("logs")    # is the folder for log file
QUERY_LOG = LOG_DIR / "queries.jsonl"    #  the log file path

#  Disclaimer enforcement for evaluation  safety
REQUIRED_DISCLAIMER_LINE = "Information only (not legal advice)."   # the exact disclaimer line the answer must start wit
DISCLAIMER_SECOND_LINE = (
    "This assistant provides general information about UK employment law and does not replace advice "
    "from a qualified solicitor, ACAS, or Citizens Advice."    # tthe second disclaimer lin
)


# INIT APP 

app = FastAPI(title="Legal RAG (Employment Law Prototype)")     # creates the fastapi app with a titl

app.add_middleware(      #  adds cors middlewar
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production nd allows all websites to call the ap ndin real production this should be more limit
    allow_credentials=True,      # tallows credential
    allow_methods=["*"],       #  allows all http metho
    allow_headers=["*"],        # tallows all header
)


# INIT MODELS VECTOR STORE 

embedder = HuggingFaceEmbeddings(model_name=EMBED_MODEL)    #  loads the embedding mode
vectorstore = FAISS.load_local(      # this tells faiss where the saved store i
    STORE_DIR,      #  gives faiss the embedding mode
    embedder,
    allow_dangerous_deserialization=True      # this allows faiss to load saved local dat
)     # tloads the faiss vector store from dis

client = OpenAI(api_key=OPENAI_API_KEY)    # creates the openai client using the api ke


#  Pydantic MODELS 

class Query(BaseModel):     #  makes the model for incoming question dat
    question: str     # says the request must have a question text fiel


class Source(BaseModel):       #  makes the model for one source ite
    title: str | None = None      # source can have a title or no titl
    url: str | None = None      # source can have a url or no ur


class AnswerResponse(BaseModel):        # makes the model for the api respons
    answer: str      #  the response has answer tex
    sources: List[Source]     #  says the response has a list of source


# Topic helpers 

PAY_KEYWORDS = {
    "pay", "paid", "wage", "wages", "salary", "underpaid", "unpaid",
    "deduction", "deductions", "minimum wage", "national minimum wage",
    "national living wage", "overtime", "payslip", "final pay", "commission", "bonus"
}     #  are words linked to pay question

HOLIDAY_KEYWORDS = {
    "holiday", "annual leave", "leave", "holiday pay", "entitlement", "accrue", "accrued",
    "bank holiday", "rolled-up"
}     # these are words linked to holiday questio

DISMISSAL_KEYWORDS = {
    "dismiss", "dismissal", "sacked", "fired", "notice", "redundancy", "unfair dismissal",
    "constructive dismissal", "appeal", "disciplinary"
}   # same again

DISCRIMINATION_KEYWORDS = {
    "discrimination", "harassment", "victimisation", "equality act", "protected characteristic",
    "race", "religion", "sex", "disability", "pregnancy", "maternity"
}      # same again


def detect_topic(q: str) -> str:      # this makes a function to guess the question topi
    text = q.lower()     # changes the question to lower cas

    pay_hits = sum(1 for k in PAY_KEYWORDS if k in text)     # counts how many pay words are in the questi
    holiday_hits = sum(1 for k in HOLIDAY_KEYWORDS if k in text)     #  how many holiday words are in the questi
    dismissal_hits = sum(1 for k in DISMISSAL_KEYWORDS if k in text)   # same again
    discrim_hits = sum(1 for k in DISCRIMINATION_KEYWORDS if k in text)     # same againthis counts how many discrimination words are in the questio

    scores = [          # this stores the pay scor
        ("pay", pay_hits),
        ("holiday", holiday_hits),     # tstores the holiday scor
        ("dismissal", dismissal_hits),         # this stores the dismissal scor
        ("discrimination", discrim_hits),     # the discrimination scor
    ]       #  list stores all topic score

    best_topic, best_score = max(scores, key=lambda x: x[1])     #  picks the topic with the biggest scor
    return best_topic if best_score > 0 else "general"      # treturns the best topic if there was a matc


def question_mentions_holiday(q: str) -> bool:     #  makes a function to check if the question mentions holida
    t = q.lower()      # this changes the question to lower cas
    return any(k in t for k in HOLIDAY_KEYWORDS)      #  returns true if any holiday word is foun


def doc_blob(doc) -> str:      # makes one big lower-case text from a docume
    url = (doc.metadata.get("url") or "").lower()      #  gets the document url and changes it to lower cas
    title = (doc.metadata.get("title") or "").lower()       #  the document title and changes it to lower cas
    content = (doc.page_content or "").lower()      # this gets the document text and changes it to lower cas
    return f"{url} {title} {content}"     #  joins url title and content into one text bloc


def doc_matches_topic(doc, topic: str, q_has_holiday: bool) -> bool:      # tmakes a function to check if one document matches the topi
    blob = doc_blob(doc)    #  builds one big text block from the docume

    # Key fix if question is PAY and user did NOT mention holiday
    # then DO NOT allow holiday documents just because they contain pay
    if topic == "pay" and not q_has_holiday:      # checks if the topic is pay and the question did not mention holida
        if "holiday" in blob or "annual leave" in blob:      #  if the document looks like a holiday documen
            return False      # says do not use this documen

    if topic == "pay":     #  checks if the topic is pay
        return any(k in blob for k in ["wage", "wages", "minimum wage", "living wage", "deduction", "payslip", "pay"])
    if topic == "holiday":      # this returns true if any pay word is found in the documen
        return any(k in blob for k in ["holiday", "annual leave", "holiday pay", "entitlement", "leave"])
    if topic == "dismissal":      # tchecks if the topic is holida
        return any(k in blob for k in ["dismiss", "dismissal", "notice", "unfair dismissal", "constructive", "redundancy"])
    if topic == "discrimination":      # this returns true if any holiday word is found in the documen
        return any(k in blob for k in ["discrimination", "equality act", "harassment", "victimisation", "protected characteristic"])

    return True       # if the topic is general this allows the docume


#  Prompt builder 

def build_prompt(question: str, docs) -> str:      #  makes a function to build the full promp
    context_parts = []       # tempty list will store the source block
    for i, d in enumerate(docs):       #  goes through each document one by on
        title = d.metadata.get("title") or f"Source {i+1}"     # tgets the document titl if missin using sourse 1
        url = d.metadata.get("url") or "Unknown URL"      #  gets the document ur if missin it use unknown url
        text = d.page_content        # this gets the document tex
        context_parts.append(        # builds one source block and adds it to the lis
            f"[Source {i+1}: {title}]\nURL: {url}\nContent:\n{text}\n"     # joins all source blocks into one big context tex
        )

    context_str = "\n\n".join(context_parts)

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
""".strip()     # this returns the full prompt text with rules, sources, and user questi


# Disclaimer enforcement 

def ensure_disclaimer(answer_text: str) -> str:
    """
    Ensures the answer starts with the exact REQUIRED_DISCLAIMER_LINE.
    Avoids duplicating disclaimer blocks.
    """       #  function makes sure the answer starts with the right disclaim
    if not answer_text:     # tchecks if the answer is empt
        return f"{REQUIRED_DISCLAIMER_LINE}\n{DISCLAIMER_SECOND_LINE}\n"       # treturns just the disclaimer lines if there is no answe

    text = answer_text.strip()      # removes spaces at the start and end

    # If it already starts correctly keep it.
    if text.startswith(REQUIRED_DISCLAIMER_LINE):       # checks if the answer already starts with the exact disclaimer lin
        return text      #  returns it unchange

    # If the disclaimer line exists somewhere else remove it and re-add at top  mean remove the old disclaimer from the wrong plac
    # prevents duplicates
    text = re.sub(r"(?im)^\s*Information only \(not legal advice\)\.\s*$\n?", "", text).strip()   #  removes lines that say Information only not legal advice then it remove extra space 

    return f"{REQUIRED_DISCLAIMER_LINE}\n{DISCLAIMER_SECOND_LINE}\n\n{text}".strip()        # adds the correct disclaimer at the top


#  Sources parsing + normalization  nd works with sources and ur

_URL_RE = re.compile(r"https?://[^\s)>\]]+", re.IGNORECASE)    # pattern finds urls in tex

def _dedupe_preserve_order(urls: List[str]) -> List[str]:      #  a function to remove duplicate urls but keep the same ordr
    seen: Set[str] = set()     # empty set remembers urls already adde
    out: List[str] = []        # this empty list stores the final url
    for u in urls:             # goes through each ur
        u2 = u.strip()        #  removes spaces around the ur
        if not u2:        # checks if the url is empt
            continue      # if empty skip i
        if u2 in seen:      #  if the url was already adde
            continue        # y skip it
        seen.add(u2)     # remembers the ur
        out.append(u2)      # adds the url to the final lis
    return out          #  returns the final url lis
     

def extract_sources_section_urls(answer_text: str) -> List[str]:        # this function gets urls only from the Sources used sectio
    """
    Extract URLs from the model's 'Sources used:' section only.
    If no section exists, returns [].
    """
    if not answer_text:      #  checks if the answer is empt
        return []          # returns an empty list if there is no answ

    m = re.search(r"(?im)^\s*Sources used\s*:\s*$", answer_text)      #  looks for a line that says Sources use
    if not m:        #  checks if no sources section was fou
        return []      # rutn an empty lis

    tail = answer_text[m.end():]     # this gets the text after the Sources usedli
    urls = _URL_RE.findall(tail)      # finds all urls in that tex
    return _dedupe_preserve_order(urls)      # removes duplicate urls and returns the final lis


def strip_existing_sources_section(answer_text: str) -> str:     # this function removes the sources section from the answe
    """
    Remove the 'Sources used:' section (if present) to avoid duplicates,
    leaving the main answer intact.
    """
    if not answer_text:      # checks if the answer is empt
        return ""      # returns empty tex

    return re.sub(r"(?ims)\n?\s*Sources used\s*:\s*\n.*\Z", "", answer_text).rstrip()       # removes the Sources used section from the end of the answe


def canonicalize_sources(answer_text: str, available_sources: List[Source]) -> Tuple[str, List[Source]]:      # function makes the final clean sources bloc
    """
    1) If model provided a 'Sources used:' section, use those URLs (deduped)
       but only keep URLs that exist in available_sources.
    2) If model didn't provide a valid section, fall back to all available_sources.
    3) Rewrite the answer to contain exactly one clean 'Sources used:' block.
    """
    url_to_source: Dict[str, Source] = {}      # empty dictionary will match urls to source object
    for s in available_sources:       # goes through each available sourc
        if s.url:          # checks if the source has a url
            url_to_source[s.url] = s       # stores the source using its url as the ke

    used_urls = extract_sources_section_urls(answer_text)      #  gets urls from the model answer sources sectio

    if used_urls:       # checks if the model gave any url
        filtered_urls = [u for u in used_urls if u in url_to_source]      #  keeps only urls that are actually in the available source
        sources_used = [url_to_source[u] for u in filtered_urls] if filtered_urls else available_sources      #  builds the final used source lis
    else:      #  runs if the model did not give any url
        sources_used = available_sources      # falls back to all available source

    body = strip_existing_sources_section(answer_text).rstrip()      #  removes any old sources section from the answer bod
    lines = ["Sources used:"]      #  starts the new sources bloc
    for s in sources_used:      #  goes through each final sourc
        if s.url:        # checks if the source has a ur
            lines.append(f"- {s.url}")      #  adds the url as a bullet lin
    sources_block = "\n".join(lines)      #  joins the sources block lines into one text bloc

    if body:        # checks if there is body tex
        new_answer = f"{body}\n\n{sources_block}"       # adds the clean sources block after the bod
    else:       #  runs if there is no body tex
        new_answer = sources_block      #  uses just the sources bloc

    return new_answer, sources_used       # returns the final clean answer and final source lis


#  Logging helpers 

def ensure_log_dir():      #  makes sure the log folder exist
    LOG_DIR.mkdir(parents=True, exist_ok=True)     # creates the log folder if it does not already exis


def doc_to_log_dict(doc) -> Dict[str, Any]:     #  makes one simple log record for a documen
    return {
        "title": doc.metadata.get("title"),      # this saves the document titl
        "url": doc.metadata.get("url"),     # saves the document ur
        "source_file": doc.metadata.get("source_file"),     # same again
        "chunk_start_word": doc.metadata.get("chunk_start_word"),    # same again
        "preview": (doc.page_content[:240] + "…") if doc.page_content and len(doc.page_content) > 240 else (doc.page_content or "")
    }      #  saves a short preview of the document tex nd if the text is long, it keeps only the first 240 character


def write_query_log(record: Dict[str, Any]) -> None:     #  writes one log record into the log fil
    ensure_log_dir()      #  makes sure the log folder exist
    with QUERY_LOG.open("a", encoding="utf-8") as f:       #  opens the log file in add mod
        f.write(json.dumps(record, ensure_ascii=False) + "\n")       # writes one json line into the log fil


# ROUTES api route-

@app.get("/")     # this is the home route
def read_root():
    return {"status": "ok", "message": "Legal RAG Employment Law API is running"}    #  returns a simple status messag


@app.post("/ask", response_model=AnswerResponse)     #  is the main ask rout
def ask(query: Query):
    question = (query.question or "").strip()     #  gets the question text and removes space
    if not question:
        raise HTTPException(status_code=400, detail="Question must not be empty.")      # checks if the question is empt nd returns an error if the question is empt

    topic = detect_topic(question)       #  guesses the topic of the questio
    q_has_holiday = question_mentions_holiday(question)   # checks if the question mentions holida

    #  Retrieve candidates nest part get possible documents 
    retrieval_method = "mmr"      #  starts with mmr as the retrieval method na
    try:       #  tries to use mmr searc
        candidates = vectorstore.max_marginal_relevance_search(    # uses the question for searc
            question,     #  asks for 12 final candidate
            k=12,
            fetch_k=40      # this first looks at 40 possible result
        )      #  runs mmr search on the vector stor
    except Exception:      # s runs if mmr search fail
        retrieval_method = "similarity_fallback"     # changes the method name to similarity fallbac
        candidates = vectorstore.similarity_search(question, k=15)       #  does a normal similarity search instea

    #  Prefer topic matching docs document matched the topic 
    topic_docs = [d for d in candidates if doc_matches_topic(d, topic, q_has_holiday)]     # keeps only candidate documents that match the topic rul

    #  Pick final docs (top 4), but ONLY add more docs that match topic
    docs = topic_docs[:4]      #  starts with the first 4 topic document

    if len(docs) < 4:      #  checks if there are fewer than 4 document
        for d in candidates:      #  goes through all candidate document
            if d in docs:      # checks if the document is already chose
                continue        # if yes skip i
            if doc_matches_topic(d, topic, q_has_holiday):      # checks if the document matches the topi
                docs.append(d)      #  adds the documen
            if len(docs) >= 4:      #  checks if there are now 4 document
                break       #  stops the loop once 4 are chose

    # If still short keep fewer docs rather than adding off-topic filler nd it is okay to use fewer documents instead of wrong one
    prompt = build_prompt(question, docs)       # builds the full prompt using the question and chosen document

    #  OpenAI call
    try:      # tries to call openai safel
        completion = client.chat.completions.create(   #  tells openai which model to us
            model=OPENAI_MODEL,      #  is the system messag
            messages=[       #  the user message with the full promp
                {"role": "system", "content": "You provide UK employment law information only (not legal advice)."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,     # this keeps the answer more stable and less rando
        )      #  sends the request to opena
    except AuthenticationError:       # truns if the api key is wron
        raise HTTPException(status_code=401, detail="OpenAI authentication failed. Check OPENAI_API_KEY.")        #  returns a 401 erro
    except RateLimitError:       # s runs if too many requests were sen
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")      #  returns a 429 erro
    except APIConnectionError:     #  runs if openai could not be reache
        raise HTTPException(status_code=503, detail="Could not connect to OpenAI. Check your internet connection.")      #  returns a 503 erro
    except APIStatusError as e:     # runs for other openai api error
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {str(e)}")      # returns a 502 error with detail
    except Exception as e:     #  runs for any other unexpected erro
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")        #  returns a 500 error with detail

    answer_text = completion.choices[0].message.content or ""     # this gets the answer text from opena

    #  Ensure disclaimer is present and starts correctly
    answer_text = ensure_disclaimer(answer_text)    #  makes sure the disclaimer is at the to

    #  Build source list dedupe by URL
    seen_urls: Set[str] = set()      #  empty set remembers urls already adde
    available_sources: List[Source] = []     #  list stores the final available source
    for d in docs:      #  goes through each chosen documen
        title = d.metadata.get("title")     #  gets the document titl
        url = d.metadata.get("url")    #  gets the document ur

        if url:     #  checks if there is a ur
            if url in seen_urls:    #  checks if the url was already adde
                continue       # if yes skip i
            seen_urls.add(url)      # remembers the ur

        available_sources.append(Source(title=title, url=url))     # adds the source object to the lis

    #  Canonicalize sources: dedupe  rewrite "Sources used once
    answer_text, sources_used = canonicalize_sources(answer_text, available_sources)     #  rebuilds the answer with one clean sources blo

    #  LOG the request  retrieval  response
    log_record = {     # this saves the current utc tim
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "question": question,      #  saves the questio
        "topic": topic,      #  the guessed topi
        "question_mentions_holiday": q_has_holiday,     #  if the question mentioned holida
        "retrieval_method": retrieval_method,      # which retrieval method was use
        "openai_model": OPENAI_MODEL,       # this saves the model nam
        "retrieved_docs": [doc_to_log_dict(d) for d in docs],    # this saves simple log records for the chosen document
        "returned_sources": [{"title": s.title, "url": s.url} for s in sources_used],    # saves the final returned sourc
        "answer": answer_text      #  saves the final answer tex
    }       #  builds the full log recor
    write_query_log(log_record)      #  writes the log record to the log fil

    return AnswerResponse(answer=answer_text, sources=sources_used)    # returns the final answer and sources to the use
