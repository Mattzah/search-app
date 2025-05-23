import aiohttp
import asyncio
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin, urlparse
import re
from datetime import datetime
import logging
from bs4 import BeautifulSoup, Comment

logger = logging.getLogger(__name__)

class ExtractedContent:
    def __init__(self, title: str, url: str, content: str, domain: str, word_count: int):
        self.title = title
        self.url = url
        self.content = content
        self.domain = domain
        self.word_count = word_count
        self.extraction_date = datetime.utcnow().isoformat()

class ContentExtractor:
    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.max_content_length = 50000  # Characters
        self.min_content_length = 200    # Characters
        
    async def extract_multiple(self, search_results: List[Any]) -> List['ExtractedContent']:
        """
        Extract content from multiple URLs concurrently
        """
        extracted_content = []
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            # Process URLs concurrently
            tasks = [self._extract_single_url(session, result) for result in search_results]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, ExtractedContent):
                    extracted_content.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"Content extraction failed: {result}")
        
        # Filter by content quality
        quality_content = [content for content in extracted_content 
                          if self._is_quality_content(content)]
        
        logger.info(f"Extracted {len(quality_content)} quality articles from {len(search_results)} URLs")
        return quality_content
    
    async def _extract_single_url(self, session: aiohttp.ClientSession, search_result: Any) -> Optional[ExtractedContent]:
        """
        Extract content from a single URL
        """
        url = search_result.url
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; GovernmentDocBot/1.0; +https://example.com/bot)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
                
                # Check content type
                content_type = response.headers.get('content-type', '').lower()
                if 'text/html' not in content_type:
                    logger.warning(f"Non-HTML content for {url}")
                    return None
                
                html_content = await response.text()
                
                # Extract clean content
                extracted = self._extract_clean_content(html_content, url)
                
                if extracted:
                    return ExtractedContent(
                        title=extracted['title'],
                        url=url,
                        content=extracted['content'],
                        domain=search_result.domain,
                        word_count=len(extracted['content'].split())
                    )
        
        except asyncio.TimeoutError:
            logger.warning(f"Timeout extracting content from {url}")
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
        
        return None
    
    def _extract_clean_content(self, html_content: str, url: str) -> Optional[Dict[str, str]]:
        """
        Extract clean text content from HTML using BeautifulSoup only
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 
                               'aside', 'advertisement', 'ads', 'form', 'iframe',
                               'noscript', 'svg', 'canvas']):
                element.decompose()
            
            # Remove comments
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()
            
            # Extract title
            title_elem = soup.find('title')
            title = title_elem.get_text().strip() if title_elem else "Untitled"
            
            # Clean up title
            title = re.sub(r'\s+', ' ', title)
            if len(title) > 100:
                title = title[:100] + "..."
            
            # Extract main content (try multiple selectors in order of preference)
            content_selectors = [
                'main',
                'article', 
                '[role="main"]',
                '.content',
                '#content',
                '.main-content',
                '.article-content',
                '.post-content',
                '.entry-content',
                '.page-content'
            ]
            
            content_text = ""
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    content_text = elements[0].get_text(separator=' ', strip=True)
                    break
            
            # Fallback: extract from body, but remove common noise
            if not content_text or len(content_text) < self.min_content_length:
                body = soup.find('body')
                if body:
                    # Remove navigation, sidebars, etc.
                    for noise in body.select('nav, .nav, .sidebar, .menu, .navigation, .breadcrumbs, .footer, .header'):
                        noise.decompose()
                    content_text = body.get_text(separator=' ', strip=True)
            
            content_text = self._clean_text(content_text)
            
            if len(content_text) >= self.min_content_length:
                return {
                    'title': title,
                    'content': content_text
                }
            
        except Exception as e:
            logger.error(f"Content extraction error for {url}: {e}")
        
        return None
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common navigation/footer text patterns
        patterns_to_remove = [
            r'Skip to main content',
            r'Skip to content',
            r'Subscribe to newsletter',
            r'Follow us on \w+',
            r'Copyright \d{4}.*?(?:\.|$)',
            r'All rights reserved.*?(?:\.|$)',
            r'Privacy Policy',
            r'Terms of Service',
            r'Cookie Policy',
            r'Sign up for.*?newsletter',
            r'Share this.*?(?:\.|$)',
            r'Print this page',
            r'Email this page',
            r'Last updated:.*?(?:\.|$)',
            r'Date modified:.*?(?:\.|$)'
        ]
        
        for pattern in patterns_to_remove:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove URLs and email addresses
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'\S+@\S+\.\S+', '', text)
        
        # Remove excessive punctuation
        text = re.sub(r'[^\w\s.,;:!?()-]', ' ', text)
        
        # Final whitespace cleanup
        text = re.sub(r'\s+', ' ', text)
        
        # Limit length
        if len(text) > self.max_content_length:
            text = text[:self.max_content_length] + "..."
        
        return text.strip()
    
    def _is_quality_content(self, content: ExtractedContent) -> bool:
        """
        Determine if extracted content meets quality thresholds
        """
        # Minimum word count
        if content.word_count < 100:
            logger.debug(f"Content too short: {content.word_count} words from {content.url}")
            return False
        
        # Check for excessive repetition (sign of boilerplate)
        words = content.content.lower().split()
        unique_words = set(words)
        uniqueness = len(unique_words) / len(words) if words else 0
        
        if uniqueness < 0.3:  # Less than 30% unique words
            logger.debug(f"Content too repetitive: {uniqueness:.2f} uniqueness from {content.url}")
            return False
        
        # Check for government/policy relevant keywords
        relevant_keywords = [
            'policy', 'government', 'minister', 'department', 'regulation',
            'legislation', 'parliament', 'federal', 'provincial', 'municipal',
            'public', 'service', 'report', 'budget', 'strategy', 'framework',
            'initiative', 'program', 'act', 'bill', 'committee', 'council',
            'administration', 'agency', 'authority', 'commission'
        ]
        
        content_lower = content.content.lower()
        keyword_count = sum(1 for keyword in relevant_keywords if keyword in content_lower)
        
        # Should have at least 2 relevant keywords
        if keyword_count < 2:
            logger.debug(f"Content not relevant: {keyword_count} keywords from {content.url}")
            return False
        
        logger.debug(f"Quality content: {content.word_count} words, {uniqueness:.2f} uniqueness, {keyword_count} keywords from {content.url}")
        return True