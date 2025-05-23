import aiohttp
import asyncio
import os
from typing import List, Dict, Any
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

class SearchResult:
    def __init__(self, title: str, url: str, snippet: str, domain: str):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.domain = domain

class SearchHandler:
    def __init__(self):
        self.serpapi_key = os.getenv("SERPAPI_API_KEY")
        self.serpapi_endpoint = "https://serpapi.com/search"
    
    async def execute_searches(self, queries: List[Any]) -> List[SearchResult]:
        """
        Execute all search queries concurrently and return filtered results
        """
        
        all_results = []
        
        async with aiohttp.ClientSession() as session:
            # Execute searches concurrently
            tasks = [self._search_single_query(session, query) for query in queries]
            search_responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, response in enumerate(search_responses):
                if isinstance(response, Exception):
                    logger.error(f"Search failed for query {i}: {response}")
                    continue
                    
                filtered_results = self._filter_results(response)
                all_results.extend(filtered_results[:5])  # Top 5 per query
        
        # Remove duplicates and limit total results
        unique_results = self._deduplicate_results(all_results)
        
        # ADD: Output logging
        logger.info(f"SEARCH_HANDLER OUTPUT - {len(unique_results)} unique results:")
        for i, result in enumerate(unique_results[:15]):  # Log all 15 results
            logger.info(f"  {i+1}. [{result.domain}] {result.title}")
        
        return unique_results[:15]  # Max 15 total results
    
    async def _search_single_query(self, session: aiohttp.ClientSession, query: Any) -> Dict[str, Any]:
        """
        Execute a single SerpAPI search query - removed site filters for comprehensive search
        """
        
        params = {
            "api_key": self.serpapi_key,
            "engine": "google",
            "q": query.query,  # Use original query without site restrictions
            "num": 10,
            "gl": "ca",  # Canada geolocation
            "hl": "en",  # English language
            "safe": "active",
            "output": "json"
        }
        
        try:
            async with session.get(self.serpapi_endpoint, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    return data
                else:
                    logger.error(f"SerpAPI error: {response.status}")
                    return {"organic_results": []}
                    
        except Exception as e:
            logger.error(f"Search request failed: {e}")
            return {"organic_results": []}
    
    def _filter_results(self, search_response: Dict[str, Any]) -> List[SearchResult]:
        """
        Filter out spam/low-quality domains, return rest in Google's ranking order
        """
        results = []
        organic_results = search_response.get("organic_results", [])
        
        logger.debug(f"FILTERING: Processing {len(organic_results)} organic results")
        
        for item in organic_results:
            url = item.get("link", "")
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            
            # Parse domain
            try:
                domain = urlparse(url).netloc.lower()
            except:
                continue
            
            # Skip low-quality domains
            if self._is_low_quality_domain(domain):
                logger.debug(f"Filtered out low-quality domain: {domain}")
                continue
            
            # Skip PDFs and non-web content for now
            if url.lower().endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx')):
                logger.debug(f"Filtered out document: {url}")
                continue
                
            results.append(SearchResult(
                title=title,
                url=url,
                snippet=snippet,
                domain=domain
            ))
        
        # Return in Google's original ranking order (no re-sorting)
        return results
    
    def _is_low_quality_domain(self, domain: str) -> bool:
        """
        Filter out obvious spam/low-quality sites
        """
        domain = domain.lower()
        
        # Spam indicators
        spam_keywords = [
            'clickbait', 'viral', 'buzz', 'listicle', 'top10', 'bestof',
            'casino', 'poker', 'gambling', 'betting', 'slots',
            'dating', 'adult', 'xxx', 'porn', 'sex',
            'freebie', 'coupon', 'deal', 'cheap', 'discount',
            'scam', 'fake', 'fraud', 'spam', 'phishing',
            'malware', 'virus', 'hack', 'crack', 'pirate',
            'get-rich', 'make-money', 'earn-cash', 'free-money'
        ]
        
        # Check for spam keywords in domain
        if any(spam in domain for spam in spam_keywords):
            return True
        
        # Check for suspicious patterns
        suspicious_patterns = [
            # Domains with excessive numbers
            len([c for c in domain if c.isdigit()]) > len(domain) * 0.3,
            # Domains with excessive hyphens
            domain.count('-') > 3,
            # Very short domains that are likely parked
            len(domain.replace('.', '').replace('-', '')) < 4,
            # Domains with suspicious TLDs (add more as needed)
            any(domain.endswith(tld) for tld in ['.tk', '.ml', '.ga', '.cf'])
        ]
        
        return any(suspicious_patterns)
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        Remove duplicate URLs and very similar titles
        """
        logger.debug(f"DEDUPLICATION: Processing {len(results)} results")
        
        seen_urls = set()
        seen_titles = set()
        unique_results = []
        
        for result in results:
            # Skip exact URL duplicates
            if result.url in seen_urls:
                logger.debug(f"Filtered duplicate URL: {result.url}")
                continue
                
            # Skip very similar titles (basic deduplication)
            title_words = set(result.title.lower().split())
            is_similar = False
            
            for seen_title in seen_titles:
                seen_words = set(seen_title.lower().split())
                if len(title_words & seen_words) / len(title_words | seen_words) > 0.8:
                    is_similar = True
                    logger.debug(f"Filtered similar title: {result.title}")
                    break
            
            if is_similar:
                continue
                
            seen_urls.add(result.url)
            seen_titles.add(result.title)
            unique_results.append(result)
        
        logger.info(f"DEDUPLICATION: {len(unique_results)} unique results from {len(results)} total")
        return unique_results