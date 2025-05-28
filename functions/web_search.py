import asyncio
import aiohttp
from aiohttp import ClientTimeout
from readability import Document
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlencode
from connection_manager import manager

# Blacklist domains to skip
BLACKLIST = {"facebook.com", "instagram.com", "tiktok.com"}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ' 
                  'AppleWebKit/537.36 (KHTML, like Gecko) ' 
                  'Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,'
              'application/xml;q=0.9,image/webp,*/*;q=0.8'
}

async def fetch_html(session: aiohttp.ClientSession, url: str, timeout: int = 5) -> str:
    try:
        async with session.get(url, timeout=ClientTimeout(total=timeout)) as resp:
            if resp.status == 200 and 'text/html' in resp.headers.get('Content-Type', ''):
                return await resp.text()
    except Exception:
        pass
    return ''

async def duckduckgo_search(session: aiohttp.ClientSession, query: str, max_results: int) -> list:
    url = f"https://html.duckduckgo.com/html/?{urlencode({'q': query})}"
    html = await fetch_html(session, url)
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    for result in soup.select('.result'):
        title_tag = result.select_one('.result__title a')
        url_text = result.select_one('.result__url')
        snippet_tag = result.select_one('.result__snippet')
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        raw_href = title_tag.get('href', '')
        href = url_text.get_text(strip=True) or raw_href
        if href.startswith('/l/?kh='):
            # DuckDuckGo redirect
            href = session._connector._resolve_redirects  # fallback
        source = href if href.startswith('http') else f"https://{href}"
        snippet = snippet_tag.get_text(strip=True) if snippet_tag else ''
        results.append({'title': title, 'source': source, 'snippet': snippet})
        if len(results) >= max_results * 2:
            break
    return results

def domain_from_url(url: str) -> str:
    try:
        return urlparse(url).netloc
    except Exception:
        return ''

async def extract_content(session: aiohttp.ClientSession, url: str, timeout: int = 5) -> str:
    domain = domain_from_url(url)
    if any(block in domain for block in BLACKLIST):
        return ''
    html = await fetch_html(session, url, timeout)
    if not html:
        return ''
    try:
        doc = Document(html)
        content = doc.summary()
        text = BeautifulSoup(content, 'html.parser').get_text(separator=' ', strip=True)
        return text[:2000] + '...' if len(text) > 2000 else text
    except Exception:
        return ''

async def enhanced_search(query: str, max_results: int = 3) -> list:
    ":""Performs a DuckDuckGo search and returns top results with extracted main content."""
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        search_results = await duckduckgo_search(session, query, max_results)
        print('search results:' + str(search_results))
        tasks = []
        for res in search_results:
            tasks.append(extract_content(session, res['source']))
        # run up to max_results concurrently and gather
        contents = await asyncio.gather(*tasks[:max_results], return_exceptions=True)
        final = []
        for idx, res in enumerate(search_results[:max_results]):
            content = contents[idx] if isinstance(contents[idx], str) else ''
            if content:
                final.append({
                    'title': res['title'],
                    'url': res['source'],
                    'domain': domain_from_url(res['source']),
                    'favicon': f"https://www.google.com/s2/favicons?domain={domain_from_url(res['source'])}&sz=32",
                    'content': content,
                    'snippet': res['snippet']
                })
                print(res['source'] + ' is ready!')
        return final


def format_results_for_llm(results: list) -> str:
    if not results:
        return "No relevant search results found."
    text = "SEARCH RESULTS:\n\n"
    for i, r in enumerate(results, 1):
        text += f"[{i}] {r['title']}\n"
        text += f"URL: {r['url']}\n"
        text += f"CONTENT: {r['content']}\n\n"
    return text

async def web_search(args):
    try:
        results = await enhanced_search(args.get('query'), 3)
        llm_results = format_results_for_llm(results)
        print(llm_results)
        await manager.send_instruction(
            session_id=args.get('session_id'),
            instruction_type="SET",
            function_name='web_search',
            args={ 'results': results },
            request_id="unique-request-id-123"
        )
        return llm_results
    except Exception as e:
        print(f'Ошибка запроса: {e}')
        return f'Ошибка запроса: {e}'