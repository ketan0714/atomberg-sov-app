import os
import requests
import re
from dotenv import load_dotenv
from googleapiclient.discovery import build
import pandas as pd
from nltk.sentiment import SentimentIntensityAnalyzer
import streamlit as st

load_dotenv()
GOOGLE_API_KEY= os.getenv("GOOGLE_API_KEY")
GOOGLE_CX=os.getenv("GOOGLE_CX")
YOUTUBE_API_KEY=os.getenv("YOUTUBE_API_KEY")

BRANDS = ["Atomberg", "Crompton", "Havells", "Usha", "Orient Electric", "Bajaj Electricals", "V-Guard",  "Polycab", "Superfan"]  #compititors

def google_search(query, num_result=20):  #google search
    service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
    response = service.cse().list(q=query, cx=GOOGLE_CX, num=10).execute()
    return response.get("items", [])


def count_mentions(text): #count mentions in post or comments
    counts = {brand : 0 for brand in BRANDS}
    for brand in BRANDS:
        if re.search(rf"\b{brand}\b", text, flags=re.IGNORECASE):
            counts[brand] += 1
    return counts
# --------------------------------------------------
score_analyzer = SentimentIntensityAnalyzer()

def analyze_sentiment(text): #will analyze the text and return positive, negative or neutral
    if not text:
        return "neutral"
    score = score_analyzer.polarity_scores(text)["compound"]
    if score >= 0.05:
        return "positive"
    elif score <= -0.05:
        return "negative"
    return "neutral"



def search_agent(keywords):
    result = []

    for kw in keywords:
        try:
            google_items = google_search(kw)
        except Exception as e:
            print(f"error google search failed for keyword :{kw} : {e}")
            google_items = []

        for rank, item in enumerate(google_items, start=1):
            text = f"{item.get("title", " ")}{item.get("snippet", " ")}"
            mention  = count_mentions(text)  # it will increase count to perticular brand if brand name is in the text
            sentiments = analyze_sentiment(text)
            for brand, count in mention.items():
                if count > 0:
                    result.append({
                        "platform": "Google",
                        "keyword": kw,
                        "rank": rank,
                        "brand": brand,
                        "text": text,
                        "sentiments": sentiments,
                        "engagments": 0
                    })
            
    df = pd.DataFrame(result)
    return df

def calculate_sov(df):
    if df.empty:
        print("no result found")
        return None
    
    #here we    

    mentions = df.groupby("brand").size().rename("mentions")

    positives = df[df["sentiments"] == "positive"].groupby('brand').size().rename("positive_mentions")

    engagments = df.groupby('brand')["engagments"].sum().rename("engagments")

    sov_df = pd.concat([mentions, positives, engagments], axis=1).fillna(0)

    #final
    sov_df["SOV_%"] = 100 * sov_df["mentions"]/sov_df["mentions"].sum()
    return sov_df.reset_index()

def generate_recommendations(sov_df):
    insights = []

    # Find top brand
    top_brand = sov_df.sort_values("SOV_%", ascending=False).iloc[0]
    insights.append(f" {top_brand['brand']} leads with {top_brand['SOV_%']:.1f}% SoV. Keep reinforcing this dominance.")

    # Find brand with lowest SoV
    low_brand = sov_df.sort_values("SOV_%").iloc[0]
    insights.append(f" {low_brand['brand']} has the lowest visibility ({low_brand['SOV_%']:.1f}%). Consider targeted campaigns for visibility.")

    # Positive mentions ratio
    sov_df["positive_ratio"] = sov_df["positive_mentions"] / sov_df["mentions"]
    strong_sentiment = sov_df.sort_values("positive_ratio", ascending=False).iloc[0]
    insights.append(f" {strong_sentiment['brand']} enjoys the best sentiment ({strong_sentiment['positive_ratio']:.0%} positive). Leverage testimonials or case studies.")

    return insights

#-----------------------------------------------------------
# streamlit
st.title(" Atomberg Share of Voice (SoV)")
st.write("Analyze brand visibility and sentiment for Atomberg vs competitors.")

keywords = ["smart fan", "smart ceiling fan", "IoT ceiling fan", "Atomberg smart fan"]
if st.button("run"):
    search_agent(keywords)
    

    df = search_agent(keywords)
    
    if df.empty:
        st.warning("not result found")
    else: 
        st.subheader("🔎 Raw Search Results")
        st.dataframe(df)


    sov_df = calculate_sov(df)
    if sov_df is not None:
        st.subheader("📈 Share of Voice (SoV)")
        st.dataframe(sov_df)
        # sov_df.to_csv("search_result.csv", index=False)
        # print("\n    share of voice (SoV)    \n")
        # print(sov_df)

        st.bar_chart(sov_df.set_index("brand")["SoV_%"])    


    st.subheader("recommendation")
    recommendations = generate_recommendations(sov_df)
    print("\n--- Recommendations ---")
    for rec in recommendations:
        st.write(rec)


    
