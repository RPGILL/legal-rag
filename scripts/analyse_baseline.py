import pandas as pd # what it does is it import the pandas so that it be can read and to be work with the csv file for this 

df = pd.read_csv("eval/summary_baseline.csv")  # this alltually read the csv file and save it in df

print("\n=== BASELINE METRICS (SCHEMA-MATCHING) ===")  # what it does is it  print a title for the first result
print("Mean latency (s):", round(df["latency_sec"].mean(), 3)) # this will print the average latency time in seconds
print("Disclaimer present (%):", round((df["has_disclaimer_hint"] == True).mean() * 100, 1))    # this print the percentage of rows where the disclaimer is there
print("Sources section present (%):", round((df["answer_lists_sources_section"] == True).mean() * 100, 1))    # it print the percentage of rows where a sources section is there
print("Answer mentions any URL (%):", round((df["answer_mentions_any_source_url"] == True).mean() * 100, 1))  # this print the number of urls shown in answers
print("Mean cited URLs:", round(df["answer_urls_count"].mean(), 2))    # this print the number of unique source urls and stuff
print("Mean unique source URLs:", round(df["unique_source_urls"].mean(), 2))     # it print the number of fake and wrong urls
print("Mean hallucinated URLs:", round(df["hallucinated_url_count"].mean(), 2))   # this print url coverage score
print("URL coverage (mean):", round(df["url_coverage"].mean(), 3))    # this  print a title for the worst hallucinated url and stuff

print("\n=== WORST (HALLUCINATED URL) EXAMPLE ===")  # it print a title for the worst hallucinated url 
bad = df[df["hallucinated_url_count"] > 0]   # what it does is it  make a new table with only rows where hallucinated urls are more than 0
if len(bad) > 0:     # well it check if there is at least one bad row
    worst = bad.sort_values(["hallucinated_url_count", "answer_urls_count"], ascending=False).iloc[0]       # this sort bad rows by highest hallucinated urls and highest answer urls
    print(worst[["question", "hallucinated_url_count", "answer_urls_count", "url_coverage", "latency_sec"]])     # this  print the question and some main values from the worst row
else:         # this print this if no bad rows were found
    print("No hallucinated URL rows found.")
