# scripts/evaluate_rag_similarity.py
# this is the file na

import json     # this lets the script read and write json da
import time      # this lets the script measure tim
import re       # this lets the script search text with patt
import uuid     # this lets the script make a random uni
from datetime import datetime, timezone    # this lets the script get date and time in u
from pathlib import Path     # this lets the script work with file pat
from urllib.parse import urlsplit, urlunsplit     # this lets the script break urls apart and put them back tog

import requests     # this lets the script send requests to the a



# Config
# this section stores the main settin

# Similarity-only server runs on port 8001
API_URL = "http://127.0.0.1:8001/ask"     # its api address to cal

EVAL_DIR = Path("eval")     #  the main eval fol
EVAL_DIR.mkdir(parents=True, exist_ok=True)     #  eval folder if it does not already exis

RUNS_DIR = EVAL_DIR / "runs"     #  folder for each ru
RUNS_DIR.mkdir(parents=True, exist_ok=True)     # runs folder if it does not already exi

# write to different filenames so we don't overwrite your MMR files
LATEST_RESULTS_JSONL = EVAL_DIR / "results_rag_similarity.jsonl"     # jsonl results file for similarity ra
LATEST_SUMMARY_CSV = EVAL_DIR / "summary_rag_similarity.csv"     # latest csv summary file for similarity ra
LATEST_SUMMARY_TMP = EVAL_DIR / "summary_rag_similarity.tmp.csv"     # temp csv file before the final latest csv is repl

# Question set file
QUESTION_FILE = Path("eval_sets") / "questions_v1.txt"     # this is the path to the questions fi

# Fallback questions (only used if file missing)
TEST_QUESTIONS = [         #  backup test questio
    "My employer has not paid my holiday pay. What can I do?",
    "How is holiday pay calculated if I work irregular hours?",     # this is one backup test ques
    "Can my employer include holiday pay in my hourly rate?",      # same again 
    "My employer has not paid my wages on payday. What should I do?",     # same again 
    "My employer deducted money from my wages without explaining why.",    # same again 
    "I think I am being paid below minimum wage. What can I do?",     # same again 
    "I was dismissed without a meeting. Is that unfair dismissal?",    # same again 
    "My employer dismissed me and refused to let me appeal.",    # same again 
    "I was treated unfairly at work because of my religion. What are my rights?",    # same again 
    "My manager is harassing me. Is this discrimination or harassment?",    # same again 
]



# Tokenization  heuristics
# --   # this section has simple text r

_WORD_RE = re.compile(r"[a-z0-9']+")     # this pattern finds words and numbers in txt
_URL_EXTRACT_RE = re.compile(r"https?://[^\s)>\"]+", re.IGNORECASE)    # finds urls in t

DISCLAIMER_PATTERNS = [       # this looks for these words
    "not legal advice",     # same again 
    "not a solicitor",      # sane again 
    "not a lawyer",       # same again 
    "informational only",      # same again 
    "information only",      # same again 
    "general information",      # same again 
    "does not replace a solicitor",     # same again 
    "does not replace legal advice",     # same again 
    "please consult a qualified solicitor",     # same again 
    "contact acas",      # same again 
    "seek advice from acas",     # same again 
    "seek advice from citizens advice",      # same again 
    "citizens advice",      # same again 
    "acas",     # same again 
]


def tokenize_words(text: str) -> set[str]:      # this makes a function to turn text into a set of wo
    if not text:       # this checks if the text is em
        return set()       # this returns an empty set if there is no tex
    return set(_WORD_RE.findall(text.lower()))       # this changes the text to lower ca


def has_disclaimer_hint(answer: str) -> bool:       # this makes a function to check if the answer has disclaimer wod
    a = (answer or "").lower()       # sure the answer is text and changes it to lower ca
    return any(p in a for p in DISCLAIMER_PATTERNS)     # t true if any disclaimer pattern is fou


def answer_lists_sources_section(answer: str) -> bool:      #  function to check if the answer has a sources sect
    a = (answer or "").lower()         # the answer is text and changes it to lower c
    return ("sources used:" in a) or ("sources:" in a)       #  true if either sources label is fou



# URL normalization + extraction


def normalize_url(url: str) -> str:       # this makes a function to clean a u
    if not url:       #  the url is emty
        return ""       #  text if there is no ur

    u = url.strip().rstrip(".,;:)")       #  punctuation from the en
    try:      # this breaks the url into part
        parts = urlsplit(u)           # removes the part after # in the ur
        parts = parts._replace(fragment="")  # drop #fragment
        u2 = urlunsplit(parts)         # cleaned url back togethe
    except Exception:        # runs if the url cleaning fai
        u2 = u          #  the old u

    if u2.endswith("/") and len(u2) > len("https://a.b/"):     # this checks if the url ends with
        parts2 = urlsplit(u2)      # breaks the url into parts agan
        if parts2.path and parts2.path != "/":      #  if the path is a real pat
            u2 = u2.rstrip("/")         # removes the last

    return u2      #  returns the cleaned u


def extract_urls_from_text(text: str) -> set[str]:       #  function to get all urls from te
    if not text:       # if the text is emty
        return set()        # this returns an empty set if there is no txt
    urls = set()       # set will store ur
    for m in _URL_EXTRACT_RE.findall(text):       # this goes through each found url
        urls.add(normalize_url(m))       # this cleans the url and adds it to the set
    return {u for u in urls if u}        # returns only non-empty url


def extract_urls_from_sources_section(answer: str) -> set[str]:     # this makes a function to get urls only from the sources sect
    if not answer:     # this checks if the answer is emptt
        return set()      # this returns an empty set if there is no ans

    m = re.search(r"(?im)^\s*Sources used\s*:\s*$", answer)       # this looks for a line that says Sources us
    if not m:       # this checks if no sources heading was fnd
        return extract_urls_from_text(answer)     # getting urls from the whole answ

    tail = answer[m.end():]       # tthe text after the Sources us
    return extract_urls_from_text(tail)        # this returns urls from that part o


def answer_mentions_any_source_url(answer: str, sources: list) -> bool:     # this makes a function to check if the answer mentions any source u
    if not answer or not sources:         # this checks if the answer is empty or there are no sou
        return False       # this returns false if either is miss
    a = (answer or "").lower()       #  answer is text and changes it to lower cas
    for s in sources:       # this goes through each sou
        u = (s or {}).get("url") or ""       # this gets the url from the sourc
        nu = normalize_url(u)       # t the url
        if nu and nu.lower() in a:       # if the clean url exists and is inside the answer te
            return True       #  true if one source url is found in the an
    return False       # false if no source url is found in the answ



# Overlap metrics
# 

def grounding_overlap_titles(answer: str, sources: list) -> float:       # this makes a function to compare answer words with source title wor
    if not answer or not sources:      # the answer is empty or there are no sour
        return 0.0         # t if missin

    aw = tokenize_words(answer)       # this the answer word
    title_words = set()      #  store all source title wo
    for s in sources:      #  goes through each sourc
        title = (s or {}).get("title") or ""         # this gets the title from the sou
        title_words |= tokenize_words(title)       # the title words into the s

    if not title_words:         # ttif there were no title wor
        return 0.0        # checks and returnn

    return round(len(aw & title_words) / len(title_words), 3)       # this works out how much the answer overlaps with title wo


def grounding_overlap_question(answer: str, question: str) -> float:        #  compare answer words with question wor
    if not answer or not question:      # e answer or question is empt
        return 0.0      #  0 if missin

    aw = tokenize_words(answer)     # tgets the answer wo
    qw = tokenize_words(question)       # tthe question wo
    if not qw:        #  checks if there are no quest
        return 0.0        #  returns 0 if there are no

    return round(len(aw & qw) / len(qw), 3)       # then rounds it to 3 decimal pl



# Coverage + hallucinations


def url_coverage_and_hallucinations(answer: str, sources: list) -> tuple[float, int, list[str], int]:       # this makes a function to check url coverage and hallucinated ur
    returned_urls = set()        # t store urls returned by the ap
    for s in sources:     # tgoes through each sour
        u = (s or {}).get("url") or ""       # the url from the sou
        nu = normalize_url(u)       #  cleans the ur
        if nu:         # the cleaned url is not emp
            returned_urls.add(nu)         # gggg the returned urls se

    answer_urls = extract_urls_from_sources_section(answer)       #  urls from the answer source

    if not returned_urls:      # tthe api returned no source ur
        hallucinated = sorted(answer_urls)       # this treats all answer urls as hallucinated u
        return 0.0, len(hallucinated), hallucinated, len(answer_urls)  #  return all this stuff

    cited = {u for u in returned_urls if u in answer_urls}       # this gets the urls that were both returned and cited in the answ
    coverage = len(cited) / len(returned_urls)       # yyyworks out the coverage sco

    hallucinated = sorted([u for u in answer_urls if u not in returned_urls])      # ttgets urls that were in the answer but not in returned sou
    return round(coverage, 3), len(hallucinated), hallucinated, len(answer_urls)    #  retun all this


def safe_csv_field(text: str) -> str:     # this makes a function to clean text before writing t
    return (text or "").replace('"', "'").replace("\n", " ").strip()      # s sure the text is not emp



# Questions loading with heading-skip


_HEADING_LINE_RE = re.compile(r"^[A-Z0-9 /_-]+\(\d+\)$")     # finds heading lines like HOLIDAY / HOLIDAY PAY (12


def is_heading_line(line: str) -> bool:      #  function to check if a line is a headi
    t = (line or "").strip()       #  the line is text and removes space
    if not t:       #  if the line is empt
        return True        # empty lines should be skip
    if t.startswith("#"):      #  if the line starts wit
        return True        # tcomment lines should be skippe
    if _HEADING_LINE_RE.match(t) and "?" not in t:      # if the line matches the heading patt
        return True        # this says it is a heading lin
    return False      # t says it is not a heading lin


def load_questions() -> list[str]:       #  a function to load ques
    if QUESTION_FILE.exists():        #  if the questions file exist
        lines = QUESTION_FILE.read_text(encoding="utf-8").splitlines()       # this reads the file and splits it into lin
        qs = []        # ist will store que
        seen = set()      #  remember questions already us
        for line in lines:     # tgoes through each li
            if is_heading_line(line):      # if the line is a hea
                continue    # if yes skip i
            q = line.strip()      # this removes spaces from the li
            if not q:       # t if the question is emp
                continue     # if yes skip 
            if q in seen:      # the question was already us
                continue        # if yes skip i
            seen.add(q)     # lll remembers the ques
            qs.append(q)      # this adds the question to the l
        if qs:      # checks if the list has questi
            return qs         # treturns the question lis
    return TEST_QUESTIONS       # file questions were found, this returns the backup q



# API call


def call_api(question: str) -> dict:       # this makes a function to call the ap
    t0 = time.time()       # stores the start t
    r = requests.post(API_URL, json={"question": question}, timeout=90)       # this sends the question to the ap
    latency = time.time() - t0       #  works out how long the request to
    r.raise_for_status()       # this checks if the request fa
    data = r.json()       # this changes the api reply into pyth
    data["_latency_sec"] = latency      # this adds the latency into the returned dat
    return data       # returns the api data



# Main
     # this section runs the full script and stuff

def main():       # this is the main func
    questions = load_questions()       #  loads all question

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]      # this makes a unique run id using date time and random tex
    run_dir = RUNS_DIR / run_id      # this makes the folder path for this run
    run_dir.mkdir(parents=True, exist_ok=True)     #  creates the run folder if it does not already ex

    run_results = run_dir / "results_rag_similarity.jsonl"     #  the jsonl results file for this run
    run_summary = run_dir / "summary_rag_similarity.csv"      #  the csv summary file for this run
    run_summary_tmp = run_dir / "summary_rag_similarity.tmp.csv"       #  the temp csv file for this run
       # this says only the similarity latest file is remove
    # Only remove similarity latest file (does NOT touch eval/results.jsonl
    if LATEST_RESULTS_JSONL.exists():     # checks if the latest similarity jsonl file already exist
        LATEST_RESULTS_JSONL.unlink()      #  deletes the old latest similarity jsonl fil

    rows = []     # empty list will store summary rows

    for q in questions:      #  goes through each questin
        try:         # tries to test the question safely
            data = call_api(q)       # sends the question to the api and gets the reply

            answer = data.get("answer", "") or ""      #  gets the answer text from the api
            sources = data.get("sources", []) or []      #  the sources list from the api

            urls = [normalize_url((s or {}).get("url") or "") for s in sources if (s or {}).get("url")]     # this gets and cleans all source urls
            urls = [u for u in urls if u]      # this keeps only non-empty urls
            unique_urls = len(set(urls))     # counts how many different urls there are

            disclaimer = has_disclaimer_hint(answer)       #  checks if the answer has disclaimer words
            sources_section = answer_lists_sources_section(answer)       # if the answer has a sources section
            mentions_url = answer_mentions_any_source_url(answer, sources)     # checks if the answer mentions any returned source url

            g_titles = grounding_overlap_titles(answer, sources)      #  gets the overlap score between answer words and source title words
            g_q = grounding_overlap_question(answer, q)      # the overlap score between answer words and question words

            coverage, halluc_count, halluc_urls, answer_urls_count = url_coverage_and_hallucinations(answer, sources)   # get coverage score hullucinate url

            rec = {       # tsaves the run id
                "run_id": run_id,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),      # saves the current utc tim
                "question": q,      # this saves the questin
                "latency_sec": round(data["_latency_sec"], 3),     # saves the latency in seco
                "num_sources": len(sources),         #  how many sources were retur
                "unique_source_urls": unique_urls,     #  saves how many different source urls there we
                "has_disclaimer_hint": disclaimer,     # saves if disclaimer words were foud
                "answer_lists_sources_section": sources_section,       # if a sources section was found
                "answer_mentions_any_source_url": mentions_url,     #  the answer mentions any source url
                "grounding_overlap_titles": g_titles,      # this the title overlap score
                "url_coverage": coverage,       # the url coverage score
                "hallucinated_url_count": halluc_count,      # aves the number of bad url
                "hallucinated_urls": halluc_urls,      # same again
                "answer_urls_count": answer_urls_count,     # same again
                "grounding_overlap_question": g_q,   # same again
                "sources": sources,      # this saves the full sources list
                "answer": answer,      # this saves the full answr
            }      # builds the full result reco

            with run_results.open("a", encoding="utf-8") as f:     # opens the run jsonl file in add mode
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")     #  writes one result line to the run jsonl fil

            with LATEST_RESULTS_JSONL.open("a", encoding="utf-8") as f:       # opens the latest similarity jsonl file in add mod
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")      # t one result line to the latest similarity jsonl fil

            rows.append(rec)       # this adds the record to the rows list
            print(f"OK(RAG_SIM): {q}  (sources={len(sources)}, latency={rec['latency_sec']}s)")        # this prints a success lin

        except Exception as e:      #  runs if something went wrng
            print(f"FAIL(RAG_SIM): {q} -> {e}")      # this prints a fail lin
            rec = {"run_id": run_id, "question": q, "error": str(e)}       # this makes a small error recod
            with run_results.open("a", encoding="utf-8") as f:     # this opens the run jsonl file in add mod
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")          #  writes the error record to the run jsonl fil
            with LATEST_RESULTS_JSONL.open("a", encoding="utf-8") as f:       # opens the latest similarity jsonl file in add mod
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")      # writes the error record to the latest similarity jsonl fil

    header = (
        "run_id,timestamp_utc,question,latency_sec,num_sources,unique_source_urls,"
        "has_disclaimer_hint,answer_lists_sources_section,answer_mentions_any_source_url,"
        "grounding_overlap_titles,url_coverage,hallucinated_url_count,"
        "answer_urls_count,grounding_overlap_question\n"
    )        # stores the csv header lin
   
    with run_summary_tmp.open("w", encoding="utf-8", newline="") as f:        #  opens the temp run csv file for writin
        f.write(header)       # writes the header lin
        for r in rows:       # goes through each saved row
            q_field = safe_csv_field(r.get("question", ""))       #  cleans the question text for cs
            f.write(      #  writes run id, time, and questio
                f"\"{r.get('run_id','')}\",\"{r.get('timestamp_utc','')}\",\"{q_field}\","       # writes latency num ources and unique source_url
                f"{r.get('latency_sec',0)},{r.get('num_sources',0)},{r.get('unique_source_urls',0)},"       # writes the true or false check
                f"{r.get('has_disclaimer_hint',False)},{r.get('answer_lists_sources_section',False)},{r.get('answer_mentions_any_source_url',False)},"
                f"{r.get('grounding_overlap_titles',0)},{r.get('url_coverage',0)},{r.get('hallucinated_url_count',0)},"        # twrites overlap, coverage, and bad url count
                f"{r.get('answer_urls_count',0)},{r.get('grounding_overlap_question',0)}\n"      # this writes answer url count and question overlp and end line 
            )
    run_summary_tmp.replace(run_summary)         # replaces the final run csv with the temp cs

    with LATEST_SUMMARY_TMP.open("w", encoding="utf-8", newline="") as f:      # opens the latest temp csv file for writin
        f.write(header)     #  writes the header lin
        for r in rows:      # goes through each saved row
            q_field = safe_csv_field(r.get("question", ""))      #  cleans the question text for csv
            f.write(       # writes run id time and questio
                f"\"{r.get('run_id','')}\",\"{r.get('timestamp_utc','')}\",\"{q_field}\","      #  writes latency, num_sources, and unique_source_ur 
                f"{r.get('latency_sec',0)},{r.get('num_sources',0)},{r.get('unique_source_urls',0)},"      #  answer url count and question overla[]
                f"{r.get('has_disclaimer_hint',False)},{r.get('answer_lists_sources_section',False)},{r.get('answer_mentions_any_source_url',False)},"        #  writes the true or false chec
                f"{r.get('grounding_overlap_titles',0)},{r.get('url_coverage',0)},{r.get('hallucinated_url_count',0)},"     #  writes overlap coverage and bad url coun and ends the line 
                f"{r.get('answer_urls_count',0)},{r.get('grounding_overlap_question',0)}\n"        # replaces the final latest csv with the temp latest cs
            )
    LATEST_SUMMARY_TMP.replace(LATEST_SUMMARY_CSV)      # this replaces the final latest csv with the temp latest csv

    print("\nSaved:")      # this prints a heading for saved fil
    print(f"- Per-run:  {run_results}")         # this prints the run jsonl file path
    print(f"- Per-run:  {run_summary}")      # this prints the run csv file path
    print(f"- Latest:   {LATEST_RESULTS_JSONL}")      #  prints the latest similarity jsonl file pa
    print(f"- Latest:   {LATEST_SUMMARY_CSV}")      # prints the latest similarity csv file pa
    print(f"\nRun ID: {run_id}")       # this prints the run id


if __name__ == "__main__":     # checks if the file is being run direcly
    main()       #  runs the main funct
