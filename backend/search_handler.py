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
        self.bing_api_key = os.getenv("BING_SEARCH_API_KEY")
        self.bing_endpoint = "https://api.bing.microsoft.com/v7.0/search"
        
        # Trusted government domains
        self.trusted_domains = {
            '.gov', '.gc.ca', '.ca', '.gov.uk', '.gov.au',
            'canada.ca', 'ontario.ca', 'toronto.ca', 'statcan.gc.ca',
            'parl.gc.ca', 'justice.gc.ca', 'fin.gc.ca'
        }
    
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
                    
                filtered_results = self._filter_and_rank_results(response)
                all_results.extend(filtered_results[:5])  # Top 5 per query
        
        # Remove duplicates and limit total results
        unique_results = self._deduplicate_results(all_results)
        return unique_results[:15]  # Max 15 total results
    
    async def _search_single_query(self, session: aiohttp.ClientSession, query: Any) -> Dict[str, Any]:
        """
        Execute a single Bing search query
        """
        headers = {
            "Ocp-Apim-Subscription-Key": self.bing_api_key,
            "User-Agent": "Mozilla/5.0 (compatible; GovernmentDocBot/1.0)"
        }
        
        # Add site filters for government domains
        enhanced_query = f"{query.query} (site:.gov OR site:.gc.ca OR site:canada.ca)"
        
        params = {
            "q": enhanced_query,
            "count": 10,
            "offset": 0,
            "mkt": "en-CA",  # Canadian market for better gov results
            "safeSearch": "Strict",
            "textDecorations": False,
            "textFormat": "Raw"
        }
        
        try:
            async with session.get(self.bing_endpoint, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.error(f"Bing API error: {response.status}")
                    return {"webPages": {"value": []}}
                    
        except Exception as e:
            logger.error(f"Search request failed: {e}")
            return {"webPages": {"value": []}}
    
    def _filter_and_rank_results(self, search_response: Dict[str, Any]) -> List[SearchResult]:
        """
        Filter and rank search results based on domain trust and relevance
        """
        results = []
        web_pages = search_response.get("webPages", {}).get("value", [])
        
        for item in web_pages:
            url = item.get("url", "")
            title = item.get("name", "")
            snippet = item.get("snippet", "")
            
            # Parse domain
            try:
                domain = urlparse(url).netloc.lower()
            except:
                continue
            
            # Score based on domain trustworthiness
            trust_score = self._calculate_trust_score(domain)
            
            # Skip low-trust domains
            if trust_score == 0:
                continue
            
            # Skip PDFs and non-web content for now
            if url.lower().endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx')):
                continue
                
            results.append(SearchResult(
                title=title,
                url=url,
                snippet=snippet,
                domain=domain
            ))
        
        # Sort by trust score (higher is better)
        results.sort(key=lambda x: self._calculate_trust_score(x.domain), reverse=True)
        return results
    
    def _calculate_trust_score(self, domain: str) -> int:
        """
        Calculate trust score for a domain (higher = more trusted)
        """
        domain = domain.lower()
        
        # Highest trust: Official government domains
        if any(trusted in domain for trusted in ['.gov', '.gc.ca', 'canada.ca']):
            return 10
            
        # High trust: Provincial/municipal government
        if any(trusted in domain for trusted in ['.ca', 'ontario.ca', 'toronto.ca']):
            return 8
            
        # Medium trust: Academic and established news
        if any(trusted in domain for trusted in ['.edu', '.ac.', 'statcan', 'parl.gc.ca']):
            return 6
            
        # Low trust: Commercial news sites
        if any(trusted in domain for trusted in ['cbc.ca', 'globalnews.ca', 'ctvnews.ca']):
            return 4
            
        # No trust: Everything else
        return 0
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        Remove duplicate URLs and similar titles
        """
        seen_urls = set()
        unique_results = []
        
        for result in results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique_results.append(result)
        
        return unique_results