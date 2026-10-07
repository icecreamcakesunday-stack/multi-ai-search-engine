from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import os
import asyncio
import requests
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Multi AI Search Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: str


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    source: str
    score: float = 0.0


def fetch_duckduckgo(query: str) -> List[Dict[str, Any]]:
    url = "https://duckduckgo.com/html/?q=" + quote_plus(query)
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    for item in soup.select(".result")[:10]:
        title = item.select_one(".result__title")
        link = item.select_one(".result__a")
        snippet = item.select_one(".result__snippet")
        if title and link:
            href = link.get("href")
            results.append({
                "title": title.get_text(" ", strip=True),
                "url": href,
                "snippet": snippet.get_text(" ", strip=True) if snippet else "",
                "source": "DuckDuckGo",
                "score": 0.75,
            })
    return results


def fetch_bing(query: str) -> List[Dict[str, Any]]:
    api_key = os.getenv("BING_API_KEY")
    if not api_key:
        return []

    url = "https://api.bing.microsoft.com/v7.0/search"
    params = {"q": query, "count": 10, "responseFilter": "Webpages"}
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return []

    results = []
    for item in payload.get("webPages", {}).get("value", [])[:10]:
        results.append({
            "title": item.get("name", "Untitled"),
            "url": item.get("url", ""),
            "snippet": item.get("snippet", ""),
            "source": "Bing",
            "score": 0.9,
        })
    return results


def fetch_brave(query: str) -> List[Dict[str, Any]]:
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        return []

    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {"Accept": "application/json", "X-Subscription-Token": api_key}
    params = {"q": query, "count": 10}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return []

    results = []
    for item in payload.get("web", {}).get("results", [])[:10]:
        results.append({
            "title": item.get("title", "Untitled"),
            "url": item.get("url", ""),
            "snippet": item.get("description", ""),
            "source": "Brave",
            "score": 0.95,
        })
    return results


def dedupe_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    deduped = []
    for result in results:
        key = result.get("url", "")
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(result)
    return deduped


def rank_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    scored = []
    for result in results:
        title = str(result.get("title", "")).lower()
        snippet = str(result.get("snippet", "")).lower()
        query_bonus = 0.15 if title or snippet else 0
        result["score"] = float(result.get("score", 0.0)) + query_bonus
        scored.append(result)
    return sorted(scored, key=lambda r: r.get("score", 0), reverse=True)


async def search_all(query: str) -> List[Dict[str, Any]]:
    loop = asyncio.get_running_loop()

    tasks = [
        loop.run_in_executor(None, fetch_duckduckgo, query),
        loop.run_in_executor(None, fetch_bing, query),
        loop.run_in_executor(None, fetch_brave, query),
    ]
    providers_results = await asyncio.gather(*tasks)

    raw_results = []
    for provider_results in providers_results:
        raw_results.extend(provider_results)

    return rank_results(dedupe_results(raw_results))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/search", response_model=List[SearchResult])
async def search(req: SearchRequest):
    if not req.query or not req.query.strip():
        raise HTTPException(400, "Query cannot be empty")

    results = []
    for item in await search_all(req.query):
        results.append(SearchResult(
            title=item.get("title", "Untitled"),
            url=item.get("url", ""),
            snippet=item.get("snippet", ""),
            source=item.get("source", "Unknown"),
            score=item.get("score", 0.0),
        ))

    return results


@app.get("/")
def index():
    return {
        "app": "Multi AI Search Engine",
        "usage": "POST /search with {\"query\": \"your search\"}",
        "notes": "Optional BING_API_KEY and BRAVE_API_KEY enable additional providers.",
    }
