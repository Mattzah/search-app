from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import asyncio
import aiohttp
import os
from urllib.parse import urljoin, urlparse
import re
from datetime import datetime
import logging

# Import helper modules (we'll create these)
from search_handler import SearchHandler
from content_extractor import ContentExtractor
from summarizer import Summarizer
from query_generator import QueryGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Search and Summarize API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class DocumentRequest(BaseModel):
    subject: str = Field(..., min_length=1, description="The main topic of the document")
    purpose: str = Field(..., min_length=1, description="The purpose of the document")
    jurisdiction: Optional[str] = Field(None, description="e.g. 'Canada', 'Ontario', 'City of Toronto'")

class SearchQuery(BaseModel):
    query: str
    category: str  # 'background', 'recent', 'policy'

class SourceSummary(BaseModel):
    title: str
    url: str
    source_summary: List[str]  # 3-4 bullet points
    domain: str
    date_accessed: str

class SearchResponse(BaseModel):
    queries: List[SearchQuery]
    summary: List[str]  # 5-7 synthesized bullet points
    sources: List[SourceSummary]
    processing_time: float

# Initialize handlers
query_gen = QueryGenerator()
search_handler = SearchHandler()
content_extractor = ContentExtractor()
summarizer = Summarizer()

@app.get("/")
async def root():
    return {"message": "Search and Summarize API", "status": "active"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/search-and-summarize", response_model=SearchResponse)
async def search_and_summarize(request: DocumentRequest):
    """
    Main endpoint that orchestrates the entire search and summarization pipeline
    """
    start_time = datetime.now()
    
    try:
        # Step 1: Generate search queries
        logger.info(f"Generating queries for subject: {request.subject}")
        queries = await query_gen.generate_queries(
            subject=request.subject,
            purpose=request.purpose,
            jurisdiction=request.jurisdiction
        )
        
        # Step 2: Execute searches
        logger.info(f"Executing {len(queries)} search queries")
        search_results = await search_handler.execute_searches(queries)
        
        # Step 3: Extract content from URLs
        logger.info(f"Extracting content from {len(search_results)} URLs")
        extracted_content = await content_extractor.extract_multiple(search_results)
        
        # Step 4: Summarize each source
        logger.info("Summarizing individual sources")
        source_summaries = await summarizer.summarize_sources(extracted_content)
        
        # Step 5: Create synthesis
        logger.info("Creating unified synthesis")
        unified_summary = await summarizer.synthesize_summary(
            source_summaries=source_summaries,
            subject=request.subject,
            purpose=request.purpose
        )
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return SearchResponse(
            queries=queries,
            summary=unified_summary,
            sources=source_summaries,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error in search_and_summarize: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.post("/generate-queries")
async def generate_queries_only(request: DocumentRequest):
    """
    Endpoint to just generate queries without executing searches
    """
    try:
        queries = await query_gen.generate_queries(
            subject=request.subject,
            purpose=request.purpose,
            jurisdiction=request.jurisdiction
        )
        return {"queries": queries}
    except Exception as e:
        logger.error(f"Error generating queries: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Query generation failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    # Ensure required environment variables are set
    required_env_vars = ["OPENAI_API_KEY", "SERPAPI_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        exit(1)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)