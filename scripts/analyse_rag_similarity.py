# scripts/analyse_rag_similarity.py    # this is the file name
import pandas as pd      # this load pandas so that the CSV files can be read 

CSV_PATH = "eval/summary_rag_similarity.csv"      # what it does is it save the path to the CSV file 

df = pd.read_csv(CSV_PATH)        # this actually read the CSV file into the  df  and a table

print("\n=== RAG SIMILARITY-ONLY METRICS ===")    #    what it does is ir  print a title 
print("Mean latency (s):", round(df["latency_sec"].mean(), 3))           # it show the time the model took to do taht
print("Mean sources returned:", round(df["num_sources"].mean(), 2))         # this show the number of the sources 
print("Mean unique sources:", round(df["unique_source_urls"].mean(), 2))      # what it does is that it show the number of different sources and stuff
print("Disclaimer present (%):", round(df["has_disclaimer_hint"].mean() * 100, 1))       # it show how is often a disclaimer was in the answer
print("Sources section present (%):", round(df["answer_lists_sources_section"].mean() * 100, 1))      # it tells sources section was in the answer how many times 
print("Answer mentions any URL (%):", round(df["answer_mentions_any_source_url"].mean() * 100, 1))    # this how many times the answer had a URL
print("Mean grounding overlap (titles):", round(df["grounding_overlap_titles"].mean(), 3))       # this is show how much the answer matched the correct titles
print("Mean grounding overlap (question):", round(df["grounding_overlap_question"].mean(), 3))      #  it tell how many times the answer matched the question
print("Mean URL coverage:", round(df["url_coverage"].mean(), 3))            # how many correct URLs were used and stuff
print("Mean hallucinated URLs:", round(df["hallucinated_url_count"].mean(), 2))      # how many fake URLs made up by teh model

print("\n=== BEST GROUNDED (TITLES) ===")        # this actually sort out groundin and pick first row and show some columns
print(df.sort_values("grounding_overlap_titles", ascending=False).iloc[0][        # it does the  sort by worst grounding pick first row and collum can be seen
    ["question", "grounding_overlap_titles", "num_sources", "unique_source_urls"]       #  it looks the row with the  fake URLs
])        # this find the slowest question and stuff

print("\n=== WORST GROUNDED (TITLES) ===")    # what it does is actually print a title
print(df.sort_values("grounding_overlap_titles").iloc[0][      # what it des is that it sort out values
    ["question", "grounding_overlap_titles", "num_sources", "unique_source_urls"] # this is url 
])

print("\n=== MOST HALLUCINATED URL EXAMPLE ===")      # again this  print a title
print(df.sort_values("hallucinated_url_count", ascending=False).iloc[0][     # again getr the most hullucinated url and stuff
    ["question", "hallucinated_url_count", "url_coverage"]   # this for the hullicinatef url 
])

print("\n=== SLOWEST QUERY ===")     # this prints again 
print(df.sort_values("latency_sec", ascending=False).iloc[0][      # this find the slowest question and stuff
    ["question", "latency_sec"]     #  thats for the latacy 
])

print("\n=== FASTEST QUERY ===")       # again this find the fastest question
print(df.sort_values("latency_sec").iloc[0][          # and  again this prints 
    ["question", "latency_sec"]       # again this find the fastest question
])
