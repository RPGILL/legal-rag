import requests    # what it does is it this lets the script download web page
from bs4 import BeautifulSoup    # this lets the script read and clean html
from pathlib import Path   # t the script work with file and folder path
import json    #  save data as json
import time    # lets the script pause between request


# SOURCES Expanded  better pay pages
# ection stores the web pages to scrap
URLS = {
    
    # DISMISSAL  DISCRIMINATION
        # these are pages about dismissal and discriminatio
    "acas_dismissals": "https://www.acas.org.uk/dismissals",     # this saves the acas dismissals page
    "acas_discrimination": "https://www.acas.org.uk/discrimination-bullying-and-harassment",      # this saves the acas discrimination page
    "gov_dismissal": "https://www.gov.uk/dismissal",       # same again
    "gov_discrimination": "https://www.gov.uk/discrimination-your-rights",    # same again
    "citizens_dismissal": "https://www.citizensadvice.org.uk/work/leaving-a-job/dismissal/",    # same again
    "citizens_discrimination": "https://www.citizensadvice.org.uk/work/discrimination-at-work/",     # same again
    "equality_ehrc": "https://www.equalityhumanrights.com/en/advice-and-guidance/employment-workplace-rights",    # same again

    
    # PAY  UNPAID WAGES  DEDUCTIONS
     # these are pages about pay unpaid wages and deductio
    "acas_pay": "https://www.acas.org.uk/pay",     # saves the acas pay page
    "acas_if_wages_not_paid": "https://www.acas.org.uk/if-wages-are-not-paid",      # this saves the acas unpaid wages page
    "acas_deductions_from_pay": "https://www.acas.org.uk/deductions-from-pay",     # same again
    "acas_final_pay": "https://www.acas.org.uk/final-pay-when-someone-leaves-a-job",    # same again
    "acas_nmw": "https://www.acas.org.uk/national-minimum-wage-entitlement",    # same again
    "gov_pay_and_work_rights": "https://www.gov.uk/pay-and-work-rights",    # same again
    "citizens_unpaid_wages": "https://www.citizensadvice.org.uk/work/pay/problems-getting-paid/",    # same again

    
    # HOLIDAY / HOLIDAY PAY
      # these are pages about holiday and holiday pay
    "acas_holiday": "https://www.acas.org.uk/holiday-sickness-leave",      # this saves the acas holiday page
    "acas_holiday_entitlement": "https://www.acas.org.uk/checking-holiday-entitlement",     # this saves the acas holiday entitlement page
    "gov_holiday_entitlement": "https://www.gov.uk/holiday-entitlement-rights",     # same again
    "gov_holiday_pay": "https://www.gov.uk/holiday-entitlement-rights/holiday-pay-the-basics",     # same again
    "citizens_holiday": "https://www.citizensadvice.org.uk/work/rights-at-work/holidays-and-holiday-pay/",     # same again
}    # this dictionary stores all source names and url

OUT_DIR = Path("data/raw")     # t the folder where scraped files will be saved
OUT_DIR.mkdir(parents=True, exist_ok=True)    # this makes the output folder if it does not already exis

HEADERS = {"User-Agent": "legal-rag-bot/0.3 (+RGU honours student project)"}    # this adds a user-agent so websites know who is making the reques


def extract_text(html: str):      #  makes a function to get useful text from html
    """    
    Improved extractor:
    - IMPORTANT FIX: captures <h1> BEFORE removing header/nav/footer (ACAS often places H1 inside <header>)
    - focuses on <main> when present (GOV.UK)
    - captures headings, paragraphs, and list items
    """
    soup = BeautifulSoup(html, "html.parser")      # this note explains what the extractor does bette
        # this reads the html into a format we can searc
    # 1) Capture title BEFORE removing headerfooternav nd   note says get the title firs
    title_text = ""     #  starts with an empty titl
    h1 = soup.find("h1")     # looks for the first h1 headin
    if h1:       # checks if an h1 was foun
        title_text = h1.get_text(" ", strip=True)     #  gets the h1 tex nd it also removes extra space

    # fallback to title tag if no H1 nd says use the page title if there is no h
    if not title_text:      # this checks if the title is still empt
        t = soup.find("title")       # this looks for the title tag
        if t:      #  checks if a title tag was foud
            title_text = t.get_text(" ", strip=True)     # this gets the title tag tex

    #  Remove non-content nd  remove parts that are not main conten
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):      # this finds all script style nav header footer, and aside tag
        tag.decompose()      # removes each of those tags from the pag

    #  Prefer <main> for GOV.UK pages nd  use the main area if it exist
    main = soup.find("main")      # this looks for the main tag
    if main:       #  checks if a main tag was foun
        soup = main      # tuses only the main part of the page

    #  Extract content blocks
    parts = []         # says get useful content piece    #  empty list will store text part
    for el in soup.find_all(["h2", "h3", "p", "li"]):     # this finds all h2 h3 p and li tag
        txt = el.get_text(" ", strip=True)      # this gets the text from the tag
        if txt and len(txt) > 2:       # checks if the text exists and is not too shor
            parts.append(txt)      # adds the text into the parts list

    #  Deduplicate while preserving order
    seen = set()      # this note says remove repeats but keep the same orde nd  empty set remembers text already adde
    cleaned = []       # this empty list will store the final clean text part
    for p in parts:      # goes through each text part
        if p not in seen:       #  checks if the text has not been added befor
            cleaned.append(p)     # adds the text to the clean lis
            seen.add(p)      # this remembers the tex

    full_text = "\n".join(cleaned).strip()      # joins all clean text parts with new line nd then removes extra space at the start and en
    return title_text.strip(), full_text     # treturns the title and the full tex


def scrape_and_save(name: str, url: str):      # makes a function to download one page and save it
    print("Fetching", url)      # this prints the url being downloade nd  downloads the web page
    r = requests.get(url, headers=HEADERS, timeout=25)     # this downloads the web pag nd  it uses the header nd waits up to 25 secon
    r.raise_for_status()       # this checks if the request faile

    title, text = extract_text(r.text)     # this gets the title and main text from the htm

    payload = {      # tsaves the short source nam
        "source": name,
        "url": url,     # this saves the source url 
        "title": title,     # this saves the page titl
        "text": text     # saves the main page tex
    }      # this builds the data to sav

    out_file = OUT_DIR / f"{name}.json"     #  makes the output file path using the source nam
    out_file.write_text(      # changes the payload into pretty json tex
        json.dumps(payload, ensure_ascii=False, indent=2),    # this saves the file using utf-8 tex
        encoding="utf-8"
    )        # this writes the json text into the output fil

    print(f"Saved {out_file} | title='{title}' | text_chars={len(text)}")      # prnt the saved file name, title, and text lengt


if __name__ == "__main__":     # tchecks if the file is being run directl
    for name, url in URLS.items():     # tgoes through each source name and url
        try:      #  tries to scrape the page safel
            scrape_and_save(name, url)      # tdownloads and saves one pag
            time.sleep(1)     # this waits 1 second before the next reques
        except Exception as e:     # this runs if there was an erro
            print("Error fetching", url, ":", e)     # this prints the url and the erro
