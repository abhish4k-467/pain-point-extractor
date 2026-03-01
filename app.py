import streamlit as st
import asyncio
import os
import traceback

# On Streamlit Community Cloud, secrets are in st.secrets, not os.environ.
# Bridge them into the environment so pydantic-ai / GroqModel can find the key.
if "GROQ_API_KEY" not in os.environ:
    try:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
    except (KeyError, FileNotFoundError):
        pass  # Will be caught by the explicit check below

from extractor import analyze_competitor


def run_async(coro):
    """Run an async coroutine from Streamlit's sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# Set page config FIRST
st.set_page_config(page_title="Competitor 'Pain Point' Extractor", layout="wide")

# Streamlit App
st.title("Competitor 'Pain Point' Extractor")
st.markdown("""
This agent scrapes negative reviews from a competitor's product and categorizes them into "Feature Requests".
""")

# Input for URL
url = st.text_input("Product Reviews URL", placeholder="https://www.example.com/product/reviews")

# Check for API Key
if not os.getenv("GROQ_API_KEY"):
    st.error("GROQ_API_KEY is not set in environment variables.")
    st.stop()

if st.button("Extract Pain Points"):
    if not url:
        st.warning("Please enter a URL.")
    else:
        with st.spinner("Scraping reviews and extracting insights..."):
            try:
                result = run_async(analyze_competitor(url))
                
                # Using columns for layout
                col1, col2 = st.columns(2)

                
                with col1:
                    st.subheader("Feature Requests")
                    for req in result.feature_requests:
                        with st.expander(f"{req.priority} Priority: {req.category}"):
                            st.write(req.description)
                            st.write("**Source Reviews:**")
                            for source in req.source_reviews:
                                st.markdown(f"- {source}")
                                
                with col2:
                    st.subheader("Extracted Reviews used for analysis")
                    for review in result.reviews:
                        st.text(f"Rating: {review.rating}/5\n\"{review.text[:200]}...\"")
                        st.markdown("---")
                        
            except Exception as e:
                st.error(f"An error occurred: {type(e).__name__}: {e}")
                st.code(traceback.format_exc())
