import openai
import os
from typing import List, Optional
from pydantic import BaseModel
import json
import logging

logger = logging.getLogger(__name__)

class SearchQuery(BaseModel):
    query: str
    category: str

class QueryGenerator:
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    async def generate_queries(self, subject: str, purpose: str, jurisdiction: Optional[str] = None) -> List[SearchQuery]:
        """
        Generate 3 targeted search queries using GPT-4o-mini
        """
        
        # ADD: Input logging
        logger.info(f"QUERY_GEN INPUT - Subject: '{subject}', Purpose: '{purpose}', Jurisdiction: '{jurisdiction}'")
        
        jurisdiction_context = f" in {jurisdiction}" if jurisdiction else ""
        
        prompt = f"""
You are an expert researcher helping government workers find relevant information for document drafting.

Generate exactly 3 search queries for the following document:
- Subject: {subject}
- Purpose: {purpose}
- Jurisdiction: {jurisdiction or "General"}

Create one query for each category:
1. BACKGROUND: Historical context, definitions, established policies{jurisdiction_context}
2. RECENT: Recent news, changes, updates, current developments{jurisdiction_context}  
3. POLICY: Government reports, official documents, regulatory information{jurisdiction_context}

Focus on:
- Government and official sources (.gov, .gc.ca, official reports)
- Factual, authoritative information
- Relevant to government document drafting

Return as JSON array with objects containing "query" and "category" fields.

Example format:
[
  {{"query": "housing affordability policy framework Canada 2025", "category": "background"}},
  {{"query": "recent housing initiatives federal government 2025", "category": "recent"}},
  {{"query": "CMHC housing strategy report government", "category": "policy"}}
]

Generate queries now:
"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a research assistant that generates precise search queries for government document research. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            content = response.choices[0].message.content.strip()
            
            # ADD: Raw LLM output logging
            logger.info(f"QUERY_GEN LLM_OUTPUT: {content}")
            
            # Extract JSON from response if wrapped in markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()
                
            queries_data = json.loads(content)
            
            # Validate and convert to SearchQuery objects
            queries = []
            for item in queries_data:
                if isinstance(item, dict) and "query" in item and "category" in item:
                    queries.append(SearchQuery(
                        query=item["query"],
                        category=item["category"]
                    ))
            
            if len(queries) != 3:
                logger.warning(f"Expected 3 queries, got {len(queries)}. Using fallback method.")
                return self._generate_fallback_queries(subject, purpose, jurisdiction)
            
            # ADD: Final output logging
            logger.info(f"QUERY_GEN OUTPUT - Generated {len(queries)} queries:")
            for i, query in enumerate(queries):
                logger.info(f"  {i+1}. [{query.category}] {query.query}")
            
            return queries
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return self._generate_fallback_queries(subject, purpose, jurisdiction)
        except Exception as e:
            logger.error(f"Query generation error: {e}")
            return self._generate_fallback_queries(subject, purpose, jurisdiction)
    
    def _generate_fallback_queries(self, subject: str, purpose: str, jurisdiction: Optional[str]) -> List[SearchQuery]:
        """
        Fallback method using templates if LLM fails
        """
        jurisdiction_suffix = f" {jurisdiction}" if jurisdiction else " government"
        
        queries = [
            SearchQuery(
                query=f"{subject} policy background{jurisdiction_suffix}",
                category="background"
            ),
            SearchQuery(
                query=f"{subject} recent news updates 2025{jurisdiction_suffix}",
                category="recent"
            ),
            SearchQuery(
                query=f"{subject} official report government policy",
                category="policy"
            )
        ]
        
        logger.info("Using fallback query generation")
        # ADD: Fallback output logging
        logger.info(f"QUERY_GEN FALLBACK OUTPUT - Generated {len(queries)} queries:")
        for i, query in enumerate(queries):
            logger.info(f"  {i+1}. [{query.category}] {query.query}")
        
        return queries