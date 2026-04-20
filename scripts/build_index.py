# scripts/build_index.py       # this is the file name

  
from pathlib import Path    # what it does is itb  lets work with folder and file paths
import json      # this help to read json files

from langchain_community.embeddings import HuggingFaceEmbeddings     # what it does is it imports the tool that turns text into number vectors and stuff
from langchain_community.vectorstores import FAISS      # this actually import faiss which stores and searches the vectors

RAW_DIR = Path("data/raw")      # what it is this is the folder where the raw json files are

SAVE_DIR = "data/faiss_langchain"      # it is the folder where the finished faiss index will be saved


EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"    # this is the embedding model nam


def load_chunks_from_raw():        # it makes a function to read the raw files and split the text into small part
    texts = []        # it is  empty list willl store the text chunk
    metadatas = []          # this is the empty list will store extra info about each chun

    for f in RAW_DIR.glob("*.json"):         # it goes through every json file in the raw foldr
        doc = json.loads(f.read_text(encoding="utf-8"))         # ot opens the file, reads the text, and turns json text into python dat

        title = doc.get("title") or doc.get("source") or f.stem      # it gets the title from the fil  if there is no titleit uses source if not souse use file name name
        url = doc.get("url", "")     # this gets the url from the fil . if there is no url, it uses an empty te

        text = doc.get("text", "")      # it gets the main text from the fil and  if there is no text, it uses empty tex

        words = text.split()    # it splits the text into word
        chunk_size = 400        # this tells each chunk will have 400 word

        for i in range(0, len(words), chunk_size):      # it loops through the words 400 at a tim
            chunk_text = " ".join(words[i:i + chunk_size]).strip()       # it joins 400 words back into one chunk of tex
            if not chunk_text:       # the  strip removes empty space at the start and en
                continue        # this checks if the chunk is empti and if it is empty skip it and go to the next chun

            texts.append(chunk_text)        # it actually  adds the chunk text to the texts list
            metadatas.append(         # it adds extra info about this chunk to the metadata lis
                {
                    "title": title,     # this saves the titl
                    "url": url,      # it saves the url
                    "source_file": f.name,     # what it does is it saves the file nam
                    "chunk_start_word": i,     # it saves the word number where this chunk start
                }
            )

    return texts, metadatas         # this sends back both list and all chunk texts and all metadat


def main():      # it is the main function that runs the full jo
    embedder = HuggingFaceEmbeddings(model_name=EMBED_MODEL)      # itr loads the embedding mode
    texts, metadatas = load_chunks_from_raw()      # it gets the chunks and metadata from the raw file

    print(f"Loaded {len(texts)} chunks from {RAW_DIR}")     # this prints how many chunks were loadd

    vectorstore = FAISS.from_texts(texts, embedder, metadatas=metadatas)     # this turns the text chunks into vector
    Path(SAVE_DIR).mkdir(parents=True, exist_ok=True)       # it then it puts them into a faiss vector store with the metadat
    vectorstore.save_local(SAVE_DIR)       # this makes the save folder if it does not already exis

    print(f"Saved FAISS index to {SAVE_DIR}")      # itt saves the faiss index to the save foldr
                # this prints a message to say the save worke

if __name__ == "__main__":      # this checks if this file is being run directy
    main()       # this runs the main functin
