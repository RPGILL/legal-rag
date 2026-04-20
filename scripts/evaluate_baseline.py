import os     # what it does is is thid lets the script work with folders files and environment settin
import json     # this lets the script read and write json da
import time     # it  the script measure til
import uuid     #  the script make a random unique i
import re     # search text with patte
from pathlib import Path    # this work with file paths in a clean w
from datetime import datetime, timezone    # the date and time in u
from typing import List, Dict, Any     # it describe what kind of data is us
from urllib.parse import urlsplit, urlunsplit     # thi  break urls apart and put them back toge

from openai import OpenAI     #  the openai cl
from openai import AuthenticationError, RateLimitError, APIConnectionError, APIStatusError    # these import common openai error



# Config
# this section stores settings for the scrip

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")     # this gets the openai api key from the environt
if not OPENAI_API_KEY:        # this checks if the api key is misin
    raise ValueError("Set OPENAI_API_KEY in environment (OPENAI_API_KEY)")        # this shows an error if the key is missin

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")    #  the model name from the environ

QUESTION_FILE = Path("eval_sets") / "questions_v1.txt"     # it stores the questin

EVAL_DIR = Path("eval")      # this eval fold
RUNS_DIR = EVAL_DIR / "runs"      #  where each run will be saved
RUNS_DIR.mkdir(parents=True, exist_ok=True)     # this is  folder if it does not already ex

LATEST_RESULTS_JSONL = EVAL_DIR / "results_baseline.jsonl"    # the latest jsonl results f
LATEST_SUMMARY_CSV = EVAL_DIR / "summary_baseline.csv"       # latest csv summary fil
LATEST_SUMMARY_TMP = EVAL_DIR / "summary_baseline.tmp.csv"      # t it is  csv file used before the final csv is rep

REQUIRED_DISCLAIMER_LINE = "Information only (not legal advice)."    # first line the answer must start wil

_URL_RE = re.compile(r"https?://[^\s)>\]]+", re.IGNORECASE)     # it pattern to find urls in te

# Headings like HOLIDAY  HOLIDAY PAY 12
_HEADING_LINE_RE = re.compile(r"^[A-Z0-9 /_-]+\(\d+\)$")     # this note explains the next patter

client = OpenAI(api_key=OPENAI_API_KEY)     # it detect heading lines in the questions fil
        # thhhis  the openai client using the api k


# URL helpers
     # this section has helper functions for url

def normalize_url(url: str) -> str:      # this makes a function to clean a url
    if not url:       # if the url is emp
        return ""         # it returns empty text if there is no u
    u = url.strip().rstrip(".,;:)]")      # paces from the start and en and removes common punctuation from the e
    try:       # tries to safely clean the url
        parts = urlsplit(u)       # url into par
        parts = parts._replace(fragment="")     # this the part after  in the u
        u2 = urlunsplit(parts)       #  the cleaned url back together
    except Exception:       #  the url could not be spli
        u2 = u       # the old url if cleaning fail

    if u2.endswith("/") and len(u2) > len("https://a.b/"):      # this checks if the url ends wit and makes sure it is not just a very short b
        p = urlsplit(u2)      # the url into parts agan
        if p.path and p.path != "/":      # this the path is a real path and not ju
            u2 = u2.rstrip("/")        # this removes the last  from the url
      # returns the cleaned url
    return u2        # function to get urls from the sources sect


def extract_sources_section_urls(answer_text: str) -> List[str]:      # if the answer is emty
    if not answer_text:      # empty list if there is no answr
        return []      #  line that says Source
    m = re.search(r"(?im)^\s*Sources used\s*:\s*$", answer_text)    # this looks for a line that says Source
    if not m:      #  if that heading was not fo
        return []       #  empty list if no sources section was f
    tail = answer_text[m.end():]      #  text after the Sources us
    urls = _URL_RE.findall(tail)       # this urls in that part of the tex

    seen = set()      # set will remember urls already se
    out = []       # list will store the final ur
    for u in urls:       # goes through each found u
        u2 = normalize_url(u)      # cleans the url
        if u2 and u2 not in seen:       # if the cleaned url is not emp
            seen.add(u2)       #  remebers the ur
            out.append(u2)     # itttt adds the url to the final li
    return out         # this  the final clean url lis


def answer_mentions_any_url(answer_text: str) -> bool:       #  function to check if the answer has any url any
    if not answer_text:        # the answer is emp
        return False       # this returns false if em
    return bool(_URL_RE.search(answer_text))        # true if any url is found in the ans



# Question loading skip headings


def is_heading_line(line: str) -> bool:       # this function to check if a line is a head
    t = (line or "").strip()     # tthe line is text and removes spa
    if not t:       # the if the line is emp
        return True        # empty lines count as heading-like lines to sk
    if t.startswith("#"):       # if the line starts wi
        return True      # comment lines should be skip
    if _HEADING_LINE_RE.match(t) and "?" not in t:      #  the line matches the heading pa
        return True      #  it is a heading lne
    return False       # this says it is not a heading li
 # this makes a function to load the questio

def load_questions() -> List[str]:      # this checks if the questions file is miss
    if not QUESTION_FILE.exists():     # this stops the script and shows an error if the file is mis
        raise FileNotFoundError(         # this reads the file and splits it into lin
            f"Could not find {QUESTION_FILE}. "        # this returns only real question line
            "This must contain the same questions used for RAG eval."     # this section works out the topic of a ques
        )
    lines = QUESTION_FILE.read_text(encoding="utf-8").splitlines()   # these are words linked to pay ques
    return [ln.strip() for ln in lines if ln.strip() and not is_heading_line(ln)]    # these are words linked to dismissal ques



# Topic detection  allow-list sources


PAY_KEYWORDS = {
    "pay", "paid", "wage", "wages", "salary", "underpaid", "unpaid",
    "deduction", "deductions", "minimum wage", "national minimum wage",
    "national living wage", "overtime", "payslip", "final pay", "commission", "bonus"
}       # these are words linked to pay questions

HOLIDAY_KEYWORDS = {
    "holiday", "annual leave", "leave", "holiday pay", "entitlement", "accrue", "accrued",
    "bank holiday", "rolled-up", "rolled up"
}     # same 
DISMISSAL_KEYWORDS = {
    "dismiss", "dismissal", "sacked", "fired", "notice", "redundancy", "unfair dismissal",
    "constructive dismissal", "appeal", "disciplinary"
}       # same 
DISCRIMINATION_KEYWORDS = {
    "discrimination", "harassment", "victimisation", "victimization", "equality act",
    "protected characteristic", "race", "religion", "sex", "disability", "pregnancy", "maternity"
}    # these are words linked to discrimination quest


def detect_topic(q: str) -> str:      # this makes a function to guess the topic of a que
    text = (q or "").lower()      # this makes sure the question is text and changes it to 
    pay_hits = sum(1 for k in PAY_KEYWORDS if k in text)      # this counts how many pay words are in the questi
    holiday_hits = sum(1 for k in HOLIDAY_KEYWORDS if k in text)     # this counts how many holiday words are in the ques
    dismissal_hits = sum(1 for k in DISMISSAL_KEYWORDS if k in text)     # this counts how many dismissal words are in the que
    discrim_hits = sum(1 for k in DISCRIMINATION_KEYWORDS if k in text)      # this counts how many discrimination words are in the ques

    scores = [
        ("holiday", holiday_hits),       # this stores the holiday sc
        ("pay", pay_hits),         # it stores the pay sco
        ("dismissal", dismissal_hits),      # the dismissal sco
        ("discrimination", discrim_hits),      # this stores the discrimination sco
    ]      # this list stores all topic scor
    best_topic, best_score = max(scores, key=lambda x: x[1])     # this picks the topic with the biggest scor
    return best_topic if best_score > 0 else "general"       # ttthe best topic if it found a mach


ALLOWLIST_BY_TOPIC: Dict[str, List[str]] = {
    "holiday": [
        "https://www.gov.uk/holiday-entitlement-rights",
        "https://www.gov.uk/holiday-entitlement-rights/holiday-pay-the-basics",
        "https://www.gov.uk/taking-holiday",
        "https://www.acas.org.uk/checking-holiday-entitlement",
        "https://www.acas.org.uk/holiday-sickness-leave",
    ],
    "pay": [        # these are allowed urls for holiday ques
        "https://www.gov.uk/national-minimum-wage-rates",
        "https://www.gov.uk/payslips",
        "https://www.acas.org.uk/pay-and-wages",
        "https://www.acas.org.uk/national-minimum-wage-entitlement",
        "https://www.citizensadvice.org.uk/work/pay/problems-getting-paid/",
    ],
    "dismissal": [          # these are allowed urls for pay questin
        "https://www.gov.uk/dismissal",
        "https://www.acas.org.uk/dismissals",
        "https://www.acas.org.uk/final-pay-when-someone-leaves-a-job",
    ],
    "discrimination": [       # these are allowed urls for dismissal questi
        "https://www.gov.uk/discrimination-your-rights",
        "https://www.acas.org.uk/discrimination-bullying-and-harassment",
    ],
    "general": [
        "https://www.acas.org.uk/",
        "https://www.gov.uk/browse/working",
        "https://www.citizensadvice.org.uk/work/",
    ],
}         # allowed urls for general question


def allowed_sources_for_question(q: str) -> List[str]:      #  function to get the allowed urls for one que
    topic = detect_topic(q)       # this works out the topic of the quest
    urls = ALLOWLIST_BY_TOPIC.get(topic, ALLOWLIST_BY_TOPIC["general"])      # topic is missing it uses the general
    out = []       # this empty list will store the final url
    seen = set()       # set will remember urls alread
    for u in urls:     #  goes through each url
        nu = normalize_url(u)      # this cleans the url
        if nu and nu not in seen:     #  if the cleaned url is not em
            seen.add(nu)       #  remembersthe url
            out.append(nu)     # the url to the final li
    return out      # this returns the final clean allowed url lis



# Baseline prompt    evaluation
# this section sends one question to openai and checks the ans

def evaluate_one(question: str) -> Dict[str, Any]:     # this makes a function to test one questin
    allowed_urls = allowed_sources_for_question(question)      # allowed urls for this ques
    allowed_block = "\n".join(f"- {u}" for u in allowed_urls)     #  urls into bullet lines for the prom

    prompt = f"""
You are an assistant providing INFORMATION ONLY about UK employment law (NOT legal advice).

CRITICAL RULES:
- You MUST start your answer with this exact line:
  {REQUIRED_DISCLAIMER_LINE}

- You MUST include a "Sources used:" section at the end.
- You MUST ONLY cite URLs from the ALLOWED SOURCES list below.
- Do NOT invent sources. Do NOT cite anything outside the allowed list.
- If you cannot answer safely using only the allowed sources, say:
  "I don't know from these sources — please consult a qualified solicitor, ACAS, or Citizens Advice."
  and then include:
  Sources used:
  (with no URLs)

OUTPUT FORMAT (follow exactly):
1) Start with: {REQUIRED_DISCLAIMER_LINE}
2) 1–3 short paragraphs answering in plain English.
3) Step-by-step suggestion (Step 1… Step 2…) if appropriate.
4) End with:
Sources used:
- <url from allowed list>
- <url from allowed list>

ALLOWED SOURCES:
{allowed_block}

User question: {question}
""".strip()     # this builds the full prompt sent to the mo

    t0 = time.time()      # this stores the start time for this queston
    try:       # this tries to call openai saf
        completion = client.chat.completions.create(
            model=OPENAI_MODEL,        # this tells openai which model to us
            messages=[       # this is the system mess
                {"role": "system", "content": "You provide UK employment law information only (not legal advice)."},
                {"role": "user", "content": prompt},      # this is the user message with all the rules and the qu
            ],
            temperature=0.2,      # this keeps the answer more stable and less ran
        )
    except (AuthenticationError, RateLimitError, APIConnectionError, APIStatusError) as e:       # this sends the request to op
        raise RuntimeError(f"OpenAI error: {e}") from e      # this catches common openai err

    latency = time.time() - t0       # raises a simpler error messag nsd  works out how long the request to
    answer = completion.choices[0].message.content or ""      # this gets the answer text from the mod

    has_disclaimer = answer.strip().startswith(REQUIRED_DISCLAIMER_LINE)      # this checks if the answer starts with the exact discla
    lists_sources_section = bool(re.search(r"(?im)^\s*Sources used\s*:\s*$", answer))     # this checks if the answer has a Sources used sec

    urls = extract_sources_section_urls(answer)      # this gets urls from the sources sec
    any_url_mentioned = answer_mentions_any_url(answer)      # this checks if any url appears anywhere in the answr

    allowed_set = {normalize_url(u) for u in allowed_urls}      # this makes a set of clean allowed ur
    hallucinated_urls = [u for u in urls if normalize_url(u) not in allowed_set]      # this finds urls in the answer that are not in the allowe
    hallucinated_url_count = len(hallucinated_urls)      # this counts how many bad urls were foun

    #  Baseline url_coverage
    # 1.0 if it cites  URL and none are hallucinated else 0.0
    url_coverage = 1.0 if (len(urls) > 0 and hallucinated_url_count == 0) else 0.0

    # Match your RAG CSV schema
    num_sources = 0     # this gives 1.0 if there is at least one good url and no bad url
    unique_source_urls = len(set(urls))

    # Titles not available in baseline => overlaps are 0
    grounding_overlap_titles = 0.0       # this note says the next fields match your other cs
    grounding_overlap_question = 0.0

    # Keep your existing "needs_citations_fail" logic too (optional but useful)
    needs_citations_fail = (      # this is set to 0 because baseline does not return sour
        (not lists_sources_section)    # this counts how many different urls are in the an
        or (lists_sources_section and len(urls) == 0)    # this counts how many different urls are in the an
        or (hallucinated_url_count > 0)       # this sets title overlap to 0
    )     # this sets question overlap to

    return {        # this saves the current utc tim
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),     # this saves the question
        "question": question,     # this saves the request time in seco
        "latency_sec": round(latency, 3),
        "openai_model": OPENAI_MODEL,       # this saves the model n

        # baseline extras
        "topic": detect_topic(question),      # this saves the guessed t
        "allowed_sources": allowed_urls,     # this saves the allowed urls for this que

        # schema-matching fields
        "num_sources": num_sources,     # this saves num_source
        "unique_source_urls": unique_source_urls,     # this saves how many different urls we
        "has_disclaimer_hint": has_disclaimer,       # this saves if the disclaimer was fo
        "answer_lists_sources_section": lists_sources_section,   # same again 
        "answer_mentions_any_source_url": any_url_mentioned,   # same again 
        "grounding_overlap_titles": grounding_overlap_titles,   # same again 
        "url_coverage": url_coverage,    # same again 
        "hallucinated_url_count": hallucinated_url_count,    # same again 
        "hallucinated_urls": hallucinated_urls,   # same again 
        "answer_urls_count": len(urls),    # same again 
        "grounding_overlap_question": grounding_overlap_question,    # same again 

        # keep for debugging/compat
        "needs_citations_fail": needs_citations_fail,
        "answer": answer,
    }     # this returns the full result for one ques



# CSV helpers
# this section has helper functions for writing the csv fi

def safe_csv_field(text: str) -> str:     # this makes a function to clean text before putting it in c
    return (text or "").replace('"', "'").replace("\n", " ").strip()     # this makes sure text is not empt


def tf(v: Any) -> str:       # this makes a function to write booleans as te
    # Write booleans as TRUE/FALSE to match your other CSVs
    if isinstance(v, bool):        # this checks if the value is true or fals
        return "TRUE" if v else "FALSE"      # this returns TRUE or FALSE as tex
    return str(v)     # if it is not a boolean, this returns it as te


def write_summary_csv(records: List[Dict[str, Any]], path: Path) -> None:    # this makes a function to write the summary csv f
    #  EXACT SAME columns as RAG summary
    header = (
        "run_id,timestamp_utc,question,latency_sec,num_sources,unique_source_urls,"
        "has_disclaimer_hint,answer_lists_sources_section,answer_mentions_any_source_url,"
        "grounding_overlap_titles,url_coverage,hallucinated_url_count,answer_urls_count,"
        "grounding_overlap_question\n"
    )         # this stores the csv header lin

    with path.open("w", encoding="utf-8", newline="") as f:     # this opens the csv file for writ
        f.write(header)       # this writes the header l
        for r in records:       #  goes each result reco
            q_field = safe_csv_field(r.get("question", ""))         # the question and cleans it for csv
            f.write(
                f"\"{r.get('run_id','')}\","        # this  the run id
                f"\"{r.get('timestamp_utc','')}\","     # the time
                f"\"{q_field}\","        # the cleaned questn
                f"{r.get('latency_sec',0)},"      # the latecy
                f"{r.get('num_sources',0)},"     # same
                f"{r.get('unique_source_urls',0)},"     # same
                f"{tf(r.get('has_disclaimer_hint',False))},"     # same
                f"{tf(r.get('answer_lists_sources_section',False))},"     # same
                f"{tf(r.get('answer_mentions_any_source_url',False))},"    # same
                f"{float(r.get('grounding_overlap_titles',0.0))},"   # same
                f"{float(r.get('url_coverage',0.0))},"  # same writes url
                f"{r.get('hallucinated_url_count',0)},"     # same
                f"{r.get('answer_urls_count',0)},"    # same
                f"{float(r.get('grounding_overlap_question',0.0))}\n"    # same
            )



# Main


def main():      # this is the main functin
    questions = load_questions()       # all questions from the file

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]     # unique run id using date, time and random tem
    run_dir = RUNS_DIR / run_id     # the folder path for this run
    run_dir.mkdir(parents=True, exist_ok=True)     # the run folder if it does not already exis

    run_results = run_dir / "results_baseline.jsonl"       #  jsonl file for this run
    run_summary = run_dir / "summary_baseline.csv"       # final csv file for this run
    run_summary_tmp = run_dir / "summary_baseline.tmp.csv"       # this is the temp csv file for this run

    if LATEST_RESULTS_JSONL.exists():      # checks if the latest jsonl file already exis
        LATEST_RESULTS_JSONL.unlink()       # this deletes the old latest jsonl fil

    records: List[Dict[str, Any]] = []     #  list will store all result rec

    for q in questions:    # goes through each question one by o
        r = evaluate_one(q)      # one question and gets the res
        r["run_id"] = run_id      # the run id into the res
        records.append(r)      # this adds the result to the record

        with run_results.open("a", encoding="utf-8") as f:      # the run jsonl file in add mod
            f.write(json.dumps(r, ensure_ascii=False) + "\n")       #  one result line into the run jsonl fil

        with LATEST_RESULTS_JSONL.open("a", encoding="utf-8") as f:    #  latest jsonl file in add mo
            f.write(json.dumps(r, ensure_ascii=False) + "\n")      #  result line into the latest jsonl fil

        print(        #  a short result line for the ques
            f"OK(BASELINE): {q} "      # tthe run summary into the temp csv fil
            f"(urls={r['answer_urls_count']}, halluc={r['hallucinated_url_count']}, "     # this replaces the final run csv with the temp c
            f"url_cov={r['url_coverage']}, latency={r['latency_sec']}s)"      # same 
        )

    write_summary_csv(records, run_summary_tmp)       #  summary into the temp latest csv fi
    run_summary_tmp.replace(run_summary)     # the final latest csv with the temp latest cs

    write_summary_csv(records, LATEST_SUMMARY_TMP)        # this prints a saved head
    LATEST_SUMMARY_TMP.replace(LATEST_SUMMARY_CSV)    # same 

    print("\nSaved:")     # this prints the run jsonl pa
    print(f"- Per-run:  {run_results}")       # same 
    print(f"- Per-run:  {run_summary}")      # same 
    print(f"- Latest:   {LATEST_RESULTS_JSONL}")    # same 
    print(f"- Latest:   {LATEST_SUMMARY_CSV}")     # same 
    print(f"\nRun ID: {run_id}")     # same 


if __name__ == "__main__":      # checks if the file is being run direct
    main()     
