import pandas as pd     # what it does it it  import pandas so that it can be read and use the csv file

df = pd.read_csv("eval/summary.csv")   # this will read the csv file and save it in df

print("\n=== BASIC METRICS ===")    # it print a title for the first results 
print("Mean latency (s):", round(df["latency_sec"].mean(), 3))  # this print the latency time in seconds
print("Mean sources returned:", round(df["num_sources"].mean(), 2))     # it print the number of sources returned
print("Mean unique sources:", round(df["unique_source_urls"].mean(), 2))     # this  print the number of unique sources
print("Disclaimer present (%):", round(df["has_disclaimer_hint"].mean() * 100, 1))   # it print percentage of rows with a disclaimer
print("Mean grounding overlap (titles):", round(df["grounding_overlap_titles"].mean(), 3))      # this print grounding score using titles
print("Mean URL coverage:", round(df["url_coverage"].mean(), 3))       # it actually print the url coverage score
print("Mean hallucinated URLs:", round(df["hallucinated_url_count"].mean(), 2))      # this print the number of fake or wrong urls

print("\n=== BEST GROUNDED ANSWER ===")       # this print a title for the best grounded answer
print(df.sort_values("grounding_overlap_titles", ascending=False).iloc[0][      # what it does is it sort rows by highest grounding score and print the top row
    ["question", "grounding_overlap_titles"]
])

print("\n=== WORST GROUNDED ANSWER ===")    # it print a title for the worst grounded answer
print(df.sort_values("grounding_overlap_titles").iloc[0][       # thid sort rows by lowest grounding score and print the first row
    ["question", "grounding_overlap_titles"]
])

print("\n=== SLOWEST QUERY ===")          # this  print a title for the slowest query
print(df.sort_values("latency_sec", ascending=False).iloc[0][        # this sort rows by highest latency and print the top row
    ["question", "latency_sec"]
])

print("\n=== FASTEST QUERY ===")        # this  print a title for the fastest query
print(df.sort_values("latency_sec").iloc[0][         # thisd sort rows by lowest latency and print the first row
    ["question", "latency_sec"]
])
