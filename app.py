from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import os
import requests
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

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


def fetch_duckduckgo(query: str) -> List[Dict[str, str]]:
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
            results.append({
                "title": title.get_text(" ", strip=True),
                "url": link.get("href"),
                "snippet": (snippet.get_text(" ", strip=True) if snippet else ""),
                "source": "DuckDuckGo",
            })
    return results


def fetch_bing(query: str) -> List[Dict[str, str]]:
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
        })
    return results


def dedupe_results(results: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    deduped = []
    for result in results:
        key = result.get("url", "")
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(result)
    return deduped


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/search", response_model=List[SearchResult])
def search(req: SearchRequest):
    if not req.query or not req.query.strip():
        raise HTTPException(400, "Query cannot be empty")

    raw_results = []
    raw_results.extend(fetch_duckduckgo(req.query))
    raw_results.extend(fetch_bing(req.query))

    results = []
    for item in dedupe_results(raw_results):
        results.append(SearchResult(
            title=item.get("title", "Untitled"),
            url=item.get("url", ""),
            snippet=item.get("snippet", ""),
            source=item.get("source", "Unknown"),
        ))

    return results


@app.get("/")
def index():
    return {
        "app": "Multi AI Search Engine",
        "usage": "POST /search with {\"query\": \"your search\"}",
        "notes": "Optional BING_API_KEY enables Bing results."
    }
