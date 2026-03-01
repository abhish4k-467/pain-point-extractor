# Competitor Pain Point Extractor

This agent scrapes negative reviews from a competitor's product page and categorizes them into actionable Feature Requests.

## Setup

1.  Make sure you have `uv` installed.
2.  Install dependencies:
    ```bash
    uv sync
    # Or just run the app, uv handles it
    ```
3.  Ensure `GROQ_API_KEY` is set in your environment variables.
    ```bash
    # Windows (PowerShell)
    $env:GROQ_API_KEY="your_api_key_here"
    # Linux/Mac
    export GROQ_API_KEY="your_api_key_here"
    ```
4.  Run the Streamlit app:
    ```bash
    uv run streamlit run app.py
    ```

## How it works

-   **Frontend**: Streamlit app for easy interaction.
-   **Agent**: Uses `pydantic-ai` with Groq's `llama-3.3-70b-versatile` model.
-   **Scraping**: Uses `crawl4ai` (powered by Playwright) to fetch review content dynamically.
-   **Analysis**: The agent extracts reviews, filters for negative sentiment (handled by LLM instruction), and groups them into Feature Requests with priority levels.
