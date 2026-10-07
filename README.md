# multi-ai-search-engine

A Python search engine that aggregates search results from multiple providers and ranks them into a single result list.

## Features
- FastAPI backend
- multi-source results from DuckDuckGo, Bing, and Brave
- deduplication by URL
- relevance-based ranking
- simple browser UI
- optional API keys for better providers

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Open the browser to `index.html` and search.

## Optional API keys

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Then add keys for:
- `BING_API_KEY`
- `BRAVE_API_KEY`

## Example API call

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query":"best ai search engine"}'
```

## Next upgrades
- add AI answer summaries
- integrate ChatGPT/Perplexity/Gemini-style answer generation
- add frontend search result cards with tabs per provider
- make ranking smarter with user feedback and embeddings
