# scripts/evaluate_rag.py  this is the file nam


import json    # tlets the script read and write json dat
import time     #  the script measure tim
import re      # tlets the script search text with pattern
import uuid     # this lets the script make a random unique id
from datetime import datetime, timezone    # t the script get date and time in utc
from pathlib import Path     # tttt the script work with file and folder path
from urllib.parse import urlsplit, urlunsplit     # this lets the script break urls apart and put them back togethr

import requests    # t script send requests to the api



# Config
    # this section stores the main setting

API_URL = "http://127.0.0.1:8000/ask"     # is the api address to cal

EVAL_DIR = Path("eval")     #  the main eval foldr
EVAL_DIR.mkdir(parents=True, exist_ok=True)    # makesthe eval folder if it does not already exis

RUNS_DIR = EVAL_DIR / "runs"     # is the folder for each run
RUNS_DIR.mkdir(parents=True, exist_ok=True)     # the runs folder if it does not already exist

# Latest outputs     # t these are the newest result file
LATEST_RESULTS_JSONL = EVAL_DIR / "results.jsonl"    #  the latest jsonl results fil
LATEST_SUMMARY_CSV = EVAL_DIR / "summary.csv"    #  is the latest csv summary fil
LATEST_SUMMARY_TMP = EVAL_DIR / "summary.tmp.csv"    #  the temp csv file before the final latest csv is replaced

# Question set file recommended
QUESTION_FILE = Path("eval_sets") / "questions_v1.txt"    # says this is the main questions fil

# Fallback questions only used if file missing
TEST_QUESTIONS = [     # tthe path to the questions fil
    "My employer has not paid my holiday pay. What can I do?",    # tthese questions are only used if the file is missin
    "How is holiday pay calculated if I work irregular hours?",      # this is one backup test question
    "Can my employer include holiday pay in my hourly rate?",         # tis one backup test questiob
    "My employer has not paid my wages on payday. What should I do?",       #   same again 
    "My employer deducted money from my wages without explaining why.",      #   same again 
    "I think I am being paid below minimum wage. What can I do?",     #   same again 
    "I was dismissed without a meeting. Is that unfair dismissal?",     #   same again 
    "My employer dismissed me and refused to let me appeal.",      #   same again 
    "I was treated unfairly at work because of my religion. What are my rights?",     #   same again 
    "My manager is harassing me. Is this discrimination or harassment?",      #   same again 
] 



# Tokenization + heuristics
   # this section has simple text rule

_WORD_RE = re.compile(r"[a-z0-9']+")     # tpattern finds words and numbers in tex
_URL_EXTRACT_RE = re.compile(r"https?://[^\s)>\"]+", re.IGNORECASE)    #  pattern finds urls in tex

DISCLAIMER_PATTERNS = [     # this looks for these words
    "not legal advice",       #   same again
    "not a solicitor",       #   same again
    "not a lawyer",      #   same again
    "informational only",     #   same again
    "information only",       #   same again
    "general information",       #   same again
    "does not replace a solicitor",      #   same again
    "does not replace legal advice",      #   same again
    "please consult a qualified solicitor",      #   same again
    "contact acas",       #   same again
    "seek advice from acas",      #   same again
    "seek advice from citizens advice",      #   same again
    "citizens advice",      #   same again
    "acas",       #   same again
]      #  list stores words that count as disclaimer hint


def tokenize_words(text: str) -> set[str]:        # t function turns text into a set of lower-case word
    """Lowercase word tokens for overlap scoring."""
    if not text:         # tchecks if the text is empty
        return set()        # this returns an empty set if there is no tex
    return set(_WORD_RE.findall(text.lower()))      #  changes the text to lower case ndthen finds word nd then returns them as a se


def has_disclaimer_hint(answer: str) -> bool:      #  makes a function to check if the answer has disclaimer word
    a = (answer or "").lower()      # tsure the answer is text and changes it to lower cas
    return any(p in a for p in DISCLAIMER_PATTERNS)     #  returns true if any disclaimer pattern is foun


def answer_lists_sources_section(answer: str) -> bool:     # t a function to check if the answer has a sources sectio
    a = (answer or "").lower()         # t the answer is text and changes it to lower cas
    return ("sources used:" in a) or ("sources:" in a)     #  returns true if either sources label is foun



# URL normalization + extraction


def normalize_url(url: str) -> str:
    """
    Normalize URLs so comparisons are stable:
    - strip whitespace + trailing punctuation
    - remove trailing slash (except domain root)
    - drop URL fragments (#...)
    """       # this function cleans a url so matching is easie
    if not url:      # tchecks if the url is empt
        return ""       #  returns empty text if there is no ur

    u = url.strip().rstrip(".,;:)")      #  removes spaces around the url nd it also removes punctuation from the end
    try:      # t tries to safely clean the url
        parts = urlsplit(u)      # tbreaks the url into part
        # Drop fragment
        parts = parts._replace(fragment="")      #  removes the part after # in the url
        # Rebuild  nd this note says build the url agai
        u2 = urlunsplit(parts)      # this puts the cleaned url back togethe
    except Exception:      # this runs if the url cleaning fail
        u2 = u      # t keeps the old url

    # Remove trailing slash unless it's just scheme host
    if u2.endswith("/") and len(u2) > len("https://a.b/"):       # tsays remove the final  in most case
        # If path is empty or  keep one slash only for host root otherwise remove trailing
        parts2 = urlsplit(u2)     # this checks if the url ends with / nd  and makes sure it is not just a very short base ur
        if parts2.path and parts2.path != "/":      # t explains when to keep the slas
            u2 = u2.rstrip("/")     # t breaks the url into parts agai
        # else keep as-is root nd this checks if the path is a real pat
         # this removes the last /
    return u2       #  returns the cleaned url


def extract_urls_from_text(text: str) -> set[str]:     # function gets all urls from tex
    """Extract URLs from any text (normalized)."""
    if not text:      #  checks if the text is empt
        return set()      # this empty set will store url
    urls = set()     #  goes through each found url
    for m in _URL_EXTRACT_RE.findall(text):        # cleans the url and adds it to the se
        urls.add(normalize_url(m))        #  returns only non-empty url
    return {u for u in urls if u}       #  function tries to get urls from the Sources used section firs
 

def extract_urls_from_sources_section(answer: str) -> set[str]:
    """
    Prefer extracting URLs ONLY from the 'Sources used:' section if present.
    Falls back to extracting from whole answer if section not found.
    """
    if not answer:      #  checks if the answer is empt
        return set()       # treturns an empty set if there is no answr

    # F a line that is exactly "Sources used" case-insensitive
    m = re.search(r"(?im)^\s*Sources used\s*:\s*$", answer)     # tsays look for a line called Sources us
    if not m:      #  checks if no sources heading was foun
        # fallbac any URL in the answer
        return extract_urls_from_text(answer)      #  gets urls from the whole answr

    tail = answer[m.end():]     #  the text after the Sources used lin
    return extract_urls_from_text(tail)      # t returns urls from that part onl


def answer_mentions_any_source_url(answer: str, sources: list) -> bool:      #  a function to check if the answer mentions any source url
    if not answer or not sources:       #  checks if the answer is empty or there are no source
        return False       # this returns false if either is missin
    a = (answer or "").lower()     #  sure the answer is text and changes it to lower cas

    for s in sources:      # goes through each sou
        u = (s or {}).get("url") or ""      #  the url from the souce
        nu = normalize_url(u)       # this cleans the url
        if nu and nu.lower() in a:        #  checks if the clean url exists and is inside the answer tex
            return True        #  returns true if one source url is found in the answe
    return False       #  returns false if no source url is foun



# Overlap metrics


def grounding_overlap_titles(answer: str, sources: list) -> float:
    """
    overlap(answer_words, all_title_words) / len(all_title_words)
    Returns 0.0 to 1.0 (rounded to 3 decimals).
    """       #  function compares answer words with source title word
    if not answer or not sources:     # checks if the answer is empty or there are no source
        return 0.0       # this returns 0 if missin

    aw = tokenize_words(answer)      # tgets the answer word

    title_words = set()       # this empty set will store all source title word
    for s in sources:        # this goes through each sourc
        title = (s or {}).get("title") or ""       #  gets the title from the sour
        title_words |= tokenize_words(title)       # tadds the title words into the se
           # t checks if there were no title word
    if not title_words:      #  returns 0 if there were no
        return 0.0      # t works out how much the answer overlaps with title wor

    score = len(aw & title_words) / len(title_words)       # trounds the score to 3 decimal place
    return round(score, 3)


def grounding_overlap_question(answer: str, question: str) -> float:      # this function compares answer words with question word
    """
    overlap(answer_words, question_words) / len(question_words)
    (Often more meaningful than title overlap.)
    """
    if not answer or not question:      #  checks if the answer or question is empt
        return 0.0     # t returns 0 if missin

    aw = tokenize_words(answer)        #  gets the answer word
    qw = tokenize_words(question)        # gets the question word

    if not qw:      #  checks if there are no question word
        return 0.0     #  returns 0 if there are non

    score = len(aw & qw) / len(qw)      # works out how much the answer overlaps with question word
    return round(score, 3)      # this rounds the score to 3 decimal place



# Coverage nd hallucinations


def url_coverage_and_hallucinations(answer: str, sources: list) -> tuple[float, int, list[str], int]:
    """
    url_coverage = (# returned URLs cited in answer sources section) / (# returned URLs)
    hallucinated_url_count = URLs cited by model that are NOT in returned URLs
    Returns:
      (coverage, halluc_count, halluc_urls, answer_urls_count)
    """       # this function checks how many source urls were cite
    returned_urls = set()      # empty set will store urls returned by the ap
    for s in sources:        #s goes through each sourc
        u = (s or {}).get("url") or ""       #  gets the url from the sour
        nu = normalize_url(u)       #  cleans the ur
        if nu:       # this checks if the cleaned url is not empt
            returned_urls.add(nu)     # this adds it to the returned urls se

    # Extract from Sources used section (preferred)
    answer_urls = extract_urls_from_sources_section(answer)     # gets urls from the answer sources secti

    if not returned_urls:      # checks if the api returned no source url
        hallucinated = sorted(answer_urls)     # ttreats all answer urls as bad url
        return 0.0, len(hallucinated), hallucinated, len(answer_urls)    # this retur all this and stuff

    cited = {u for u in returned_urls if u in answer_urls}       # tthe urls that were both returned and cited in the answe
    coverage = len(cited) / len(returned_urls)      # t works out the coverage scor

    hallucinated = sorted([u for u in answer_urls if u not in returned_urls])      #  urls that were in the answer but not in the returned source
    return round(coverage, 3), len(hallucinated), hallucinated, len(answer_urls)    #  retur all thids 


def safe_csv_field(text: str) -> str:    # this makes a function to clean text before writing to cs
    return (text or "").replace('"', "'").replace("\n", " ").strip()     #  makes sure the text is not empt



# Questions loading with heading-skip


_HEADING_LINE_RE = re.compile(r"^[A-Z0-9 /_-]+\(\d+\)$")     # this pattern finds heading lines like DISMISSAL13


def is_heading_line(line: str) -> bool:        #  function checks if a line is just a headin
    """
    Detects lines like:
      HOLIDAY / HOLIDAY PAY (12)
      DISMISSAL (13)
    so they don't get sent as questions.
    """
    t = (line or "").strip()     #  makes sure the line is text and removes spac
    if not t:       #  checks if the line is empt
        return True       #  says empty lines should be skippe
    if t.startswith("#"):     # this checks if the line starts wit this hash
        return True       #  says comment lines should be skipp
    if _HEADING_LINE_RE.match(t) and "?" not in t:      # tchecks if the line matches the heading patt
        return True       # this says it is a heading lin
    return False        # this says it is not a heading lin


def load_questions() -> list[str]:    #  makes a function to load questio
    if QUESTION_FILE.exists():       # this checks if the questions file exis
        lines = QUESTION_FILE.read_text(encoding="utf-8").splitlines()    #  reads the file and splits it into line
        qs = []       # tempty list will store question
        seen = set()     # set will remember questions already use
        for line in lines:      # s goes through each lin
            if is_heading_line(line):      #  checks if the line is a headin
                continue     # if yes skip it
            q = line.strip()      #  removes spaces from the lin
            if not q:       #  checks if the question is empt
                continue        # if yes skip it
            if q in seen:     # t checks if the question was already use
                continue
            seen.add(q)      # tremembers the questio
            qs.append(q)     # this adds the question to the lis
        if qs:          # this checks if the list has question
            return qs      #  returns the question lis
    return TEST_QUESTIONS     # if no file questions were found this returns the backup questio



# API call


def call_api(question: str) -> dict:      # this makes a function to call the ap
    t0 = time.time()      #  stores the start tim
    r = requests.post(API_URL, json={"question": question}, timeout=90)      # s sends the question to the ap
    latency = time.time() - t0     #  works out how long the request too
    r.raise_for_status()    # t checks if the request faile
    data = r.json()       #  adds the latency into the returned dat
    data["_latency_sec"] = latency    # this returns the api dat
    return data


# Main


def main():      #  is the main functio
    questions = load_questions()      # s loads all question

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]     # this makes a unique run id using date time and random tex
    run_dir = RUNS_DIR / run_id      # t makes the folder path for this ru
    run_dir.mkdir(parents=True, exist_ok=True)      # tcreates the run folder if it does not already exis

    run_results = run_dir / "results.jsonl"    # is the jsonl results file for this ru
    run_summary = run_dir / "summary.csv"      # this is the csv summary file for this ru
    run_summary_tmp = run_dir / "summary.tmp.csv"     # the temp csv file for this r

    # overwrite latest JSONL each run
    if LATEST_RESULTS_JSONL.exists():      #  checks if the latest jsonl file already exist
        LATEST_RESULTS_JSONL.unlink()      #  deletes the old latest jsonl fil

    rows = []     # t empty list will store summary row

    for q in questions:    # goes through each questio
        try:      # this tries to test the question safel
            data = call_api(q)     #  sends the question to the api and gets the repl

            answer = data.get("answer", "") or ""        # t gets the answer text from the ap
            sources = data.get("sources", []) or []      # tgets the sources list from the ap

            urls = [normalize_url(s.get("url") or "") for s in sources if s.get("url")]      #  gets and cleans all source url
            urls = [u for u in urls if u]      # keeps only non-empty url
            unique_urls = len(set(urls))     # counts how many different urls there ar

            disclaimer = has_disclaimer_hint(answer)     #  checks if the answer has disclaimer word
            sources_section = answer_lists_sources_section(answer)      # tif the answer has a sources sectio
            mentions_url = answer_mentions_any_source_url(answer, sources)       #  answer mentions any returned source ur

            g_titles = grounding_overlap_titles(answer, sources)      # the overlap score between answer words and source title word
            g_q = grounding_overlap_question(answer, q)       # t gets the overlap score between answer words and question word

            coverage, halluc_count, halluc_urls, answer_urls_count = url_coverage_and_hallucinations(answer, sources)   #  get al thisd 

            rec = {      # this saves the run id
                "run_id": run_id,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),     #  saves the current utc tim
                "question": q,     # this saves the questio
                "latency_sec": round(data["_latency_sec"], 3),    # same again
                "num_sources": len(sources),      # same again
                "unique_source_urls": unique_urls,     # same again
                "has_disclaimer_hint": disclaimer,     # same again
                "answer_lists_sources_section": sources_section,    # same again
                "answer_mentions_any_source_url": mentions_url,    # same again
                "grounding_overlap_titles": g_titles,    # same again
                "url_coverage": coverage,    # same again
                "hallucinated_url_count": halluc_count,     # same again
                "hallucinated_urls": halluc_urls,     # same again
                # extra optional but useful
                "answer_urls_count": answer_urls_count,    # same again
                "grounding_overlap_question": g_q,    # same again
                "sources": sources,    # same again
                "answer": answer,    # same again
            }

            with run_results.open("a", encoding="utf-8") as f:      # topens the run jsonl file in add mod
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")      # writes one result line to the run jsonl fil

            with LATEST_RESULTS_JSONL.open("a", encoding="utf-8") as f:      # t opens the latest jsonl file in add mod
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")      # writes one result line to the latest jsonl fil

            rows.append(rec)      # tadds the record to the rows lis
            print(f"OK: {q}  (sources={len(sources)}, latency={rec['latency_sec']}s)")      # s prints a success lin

        except Exception as e:      # this runs if something went wro
            print(f"FAIL: {q} -> {e}")       #  prints a fail lin
            rec = {"run_id": run_id, "question": q, "error": str(e)}      # makes a small error recor
            with run_results.open("a", encoding="utf-8") as f:        # topens the run jsonl file in add mod
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")      # writes the error record to the run jsonl fil
            with LATEST_RESULTS_JSONL.open("a", encoding="utf-8") as f:       #  the latest jsonl file in add mod
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")      # tthe error record to the latest jsonl fil

    #  Keep your original summary columns plus two extra at the end
    header = (          # t stores the csv header lin
        "run_id,timestamp_utc,question,latency_sec,num_sources,unique_source_urls,"
        "has_disclaimer_hint,answer_lists_sources_section,answer_mentions_any_source_url,"
        "grounding_overlap_titles,url_coverage,hallucinated_url_count,"
        "answer_urls_count,grounding_overlap_question\n"      # ththe temp run csv file for writin
    )

    with run_summary_tmp.open("w", encoding="utf-8", newline="") as f:      #  writes the header lin
        f.write(header)      #  goes through each saved ro
        for r in rows:        # this cleans the question text for cs
            q_field = safe_csv_field(r.get("question", ""))     # writes run id time and questi
            f.write(
                f"\"{r.get('run_id','')}\",\"{r.get('timestamp_utc','')}\",\"{q_field}\","      # this writes latency num_sources and unique_source_url
                f"{r.get('latency_sec',0)},{r.get('num_sources',0)},{r.get('unique_source_urls',0)},"      #  the true or false check
                f"{r.get('has_disclaimer_hint',False)},{r.get('answer_lists_sources_section',False)},{r.get('answer_mentions_any_source_url',False)},"    # this writes the true or false check
                f"{r.get('grounding_overlap_titles',0)},{r.get('url_coverage',0)},{r.get('hallucinated_url_count',0)},"      # same again
                f"{r.get('answer_urls_count',0)},{r.get('grounding_overlap_question',0)}\n"      # same again
            )
    run_summary_tmp.replace(run_summary)      # replaces the final run csv with the temp csv

    # Latest summary with temp replace
    with LATEST_SUMMARY_TMP.open("w", encoding="utf-8", newline="") as f:       # topens the latest temp csv file for writin
        f.write(header)       # this writes the header lin
        for r in rows:      #  goes through each saved ro
            q_field = safe_csv_field(r.get("question", ""))     # tcleans the question text for cs
            f.write(      # twrites run id time, and questin
                f"\"{r.get('run_id','')}\",\"{r.get('timestamp_utc','')}\",\"{q_field}\","       # this writes latency, num_sources, and unique_source_url
                f"{r.get('latency_sec',0)},{r.get('num_sources',0)},{r.get('unique_source_urls',0)},"       # this writes the true or false check
                f"{r.get('has_disclaimer_hint',False)},{r.get('answer_lists_sources_section',False)},{r.get('answer_mentions_any_source_url',False)},"      # this writes the true or false check
                f"{r.get('grounding_overlap_titles',0)},{r.get('url_coverage',0)},{r.get('hallucinated_url_count',0)},"       # this writes the true or false check
                f"{r.get('answer_urls_count',0)},{r.get('grounding_overlap_question',0)}\n"       # this writes the true or false check
            )
    LATEST_SUMMARY_TMP.replace(LATEST_SUMMARY_CSV)       # treplaces the final latest csv with the temp latest cs

    print("\nSaved:")      # tprints a heading for saved file
    print(f"- Per-run:  {run_results}")       # rints the run jsonl file pat
    print(f"- Per-run:  {run_summary}")     # this prints the run csv file pa
    print(f"- Latest:   {LATEST_RESULTS_JSONL}")      # prints the latest jsonl file pat
    print(f"- Latest:   {LATEST_SUMMARY_CSV}")       #  the latest csv file pat
    print(f"\nRun ID: {run_id}")          #  prints the run i


if __name__ == "__main__":     # checks if the file is being run directl
    main()      #  runs the main functi
