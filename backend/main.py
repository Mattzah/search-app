from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DirectionsInput(BaseModel):
    directions: str

class SearchQuery(BaseModel):
    query: str

class QueryResponse(BaseModel):
    queries: List[str]

class SearchResponse(BaseModel):
    results: List[dict]

@app.get("/")
async def root():
    return {"message": "Search and Summarize API"}

@app.post("/generate-queries", response_model=QueryResponse)
async def generate_queries(input_data: DirectionsInput):
    # Placeholder - will implement LLM logic later
    return QueryResponse(queries=["placeholder query 1", "placeholder query 2"])

@app.post("/search", response_model=SearchResponse)
async def search_content(queries: List[SearchQuery]):
    # Placeholder - will implement search logic later
    return SearchResponse(results=[{"content": "placeholder search results"}])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)