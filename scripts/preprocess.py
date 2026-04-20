from pathlib import Path      # what it does is it  this lets the script work with file and folder path
import json     # the script read and write json data

RAW_DIR = Path("data/raw")     # the folder where the raw json files are and stuff
OUT_DIR = Path("data/chunks")     #  folder where the chunk files will be saved
OUT_DIR.mkdir(parents=True, exist_ok=True)     # makes output folder if it does not already exist    

CHUNK_WORDS = 400     #  each chunk should have 400 word

def chunk_text(text, size=CHUNK_WORDS):       #  function to split text into small chunks
    words = text.split()      # this splits the text into words
    for i in range(0, len(words), size):      # goes through the words in steps of 400
        yield " ".join(words[i:i+size])     # this joins each group of words into one chunks and yield gives back one chunk at a tim

for f in RAW_DIR.glob("*.json"):      # this goes through every json file in the raw foldr
    doc = json.loads(f.read_text(encoding="utf-8"))      # opens the file reads the text, and turns json text into python data
    chunks = list(chunk_text(doc.get("text","")))    #  gets the text from the fil and if there is no text it uses empty tex nd then then it splits the text into chunk nd then it turns the chunks into a lis
    out_file = OUT_DIR / f"{f.stem}.jsonl"    #  makes the output file name nd it uses the same file name but saves it as jsonl
    with out_file.open("w", encoding="utf-8") as wf:     # opens the output file for writin
        for idx, chunk in enumerate(chunks):     # goes through each chunk one by one nd idx is the chunk numbr
            rec = {     #  makes an id using the file name and chunk numbe
                "id": f"{f.stem}_{idx}",     #  gets the title from the fil nd if missing, it uses empty tex
                "title": doc.get("title",""),      # this gets the title from the fil
                "url": doc.get("url",""),      # gets the url from the fil nd if missing it uses empty text
                "text": chunk        # stores the chunk text
            }        # this builds one chunk recor
            wf.write(json.dumps(rec, ensure_ascii=False) + "\n")      # changes the record into json text nf then writes it to the fil nd each record goes on a new lin
    print("Wrote", out_file, "chunks:", len(chunks))    #  prints the file name and how many chunks were writte
