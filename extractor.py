import asyncio
import os
import re
import httpx
from bs4 import BeautifulSoup
from pydantic_ai import Agent
from pydantic_ai.models.groq import GroqModel
from models import ExtractedData, Review, FeatureRequest


MAX_CONTENT_CHARS = 6000

# Realistic browser headers so sites don't block the request
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_agent: Agent | None = None

def _get_agent() -> Agent:
    global _agent
    if _agent is None:
        model = GroqModel("openai/gpt-oss-20b")
        _agent = Agent(
            model,
            output_type=ExtractedData,
            retries=3,
            system_prompt=(
                "You extract negative reviews (1-3 stars) from product review text and categorize pain points.\n"
                "\n"
                "You MUST respond with a JSON object matching this exact schema:\n"
                "{\n"
                '  "reviews": [{"text": "<review text>", "rating": <1-5 int>}, ...],\n'
                '  "feature_requests": [{"category": "<short label>", "description": "<what to improve>", '
                '"source_reviews": ["<brief excerpt from review>", ...], "priority": "High"|"Medium"|"Low"}, ...]\n'
                "}\n"
                "\n"
                "Rules:\n"
                "- Only include reviews with rating 1, 2, or 3.\n"
                "- source_reviews must be a list of SHORT string excerpts, not numbers.\n"
                "- priority must be exactly one of: High, Medium, Low (capitalized).\n"
                "- Do NOT include any explanation or reasoning. Output ONLY the JSON."
            ),
        )
    return _agent


def _find_review_section(text: str) -> str:
    """Try to locate and extract the review section from the page text."""
    review_section_markers = [
        r"Top reviews from",
        r"Top reviews\b",
        r"Customer reviews",
        r"Most relevant reviews",
        r"Reviews with images",
        r"Most helpful reviews",
    ]
    for pattern in review_section_markers:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return text[m.start():]
    # No known section marker — return the second half (reviews are usually at the bottom)
    halfway = len(text) // 2
    return text[halfway:]


def _clean_review_text(text: str) -> str:
    """Clean extracted review section: remove URLs, boilerplate, and compress."""
    # Remove raw URLs
    text = re.sub(r'https?://\S+', '', text)
    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove very short lines (navigation fragments)
    lines = text.splitlines()
    lines = [l.strip() for l in lines if len(l.strip()) >= 15]
    return "\n".join(lines)


async def _scrape_reviews(url: str) -> str:
    """Scrape the page with httpx + BeautifulSoup and return cleaned review text.

    This replaces the Playwright-based crawl4ai approach so the app can run
    on Streamlit Community Cloud without any browser binary dependencies.
    """
    print(f"Scraping {url}...")

    async with httpx.AsyncClient(
        headers=_HEADERS, follow_redirects=True, timeout=30
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove non-content elements
    for tag in soup(
        ["script", "style", "nav", "header", "footer", "aside", "noscript", "iframe"]
    ):
        tag.decompose()

    # Also remove common boilerplate by class/id patterns
    for el in soup.find_all(
        attrs={
            "class": re.compile(
                r"nav|header|footer|sidebar|cookie|banner|ad-|promo|newsletter",
                re.IGNORECASE,
            )
        }
    ):
        el.decompose()

    page_text = soup.get_text(separator="\n")

    # Step 1: Find the reviews section
    review_section = _find_review_section(page_text)
    # Step 2: Clean out URLs, short lines
    cleaned = _clean_review_text(review_section)
    # Step 3: Truncate to fit token budget
    if len(cleaned) > MAX_CONTENT_CHARS:
        cleaned = cleaned[:MAX_CONTENT_CHARS]

    print(
        f"Scraped: {len(page_text)} chars → review section: "
        f"{len(review_section)} chars → cleaned: {len(cleaned)} chars"
    )
    return cleaned


async def analyze_competitor(url: str):
    """Scrape reviews then analyze them with the LLM."""
    if not os.getenv("GROQ_API_KEY"):
        raise ValueError("GROQ_API_KEY environment variable is not set")

    # Step 1: scrape outside the agent (no tool overhead)
    reviews_text = await _scrape_reviews(url)
    if not reviews_text.strip():
        raise ValueError("No review content found on the page.")

    # Step 2: pass scraped text directly as the user prompt
    agent = _get_agent()
    result = await agent.run(
        f"Reviews from {url}:\n\n{reviews_text}",
    )
    return result.output
