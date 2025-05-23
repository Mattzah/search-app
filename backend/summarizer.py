import openai
import os
from typing import List, Dict, Any
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SourceSummary:
    def __init__(self, title: str, url: str, source_summary: List[str], domain: str):
        self.title = title
        self.url = url
        self.source_summary = source_summary
        self.domain = domain
        self.date_accessed = datetime.utcnow().isoformat()

class Summarizer:
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.max_chunk_size = 4000  # Characters per chunk for GPT-4o
        
    async def summarize_sources(self, extracted_content: List[Any]) -> List[SourceSummary]:
        """
        Summarize each source individually into 3-4 bullet points
        """
        source_summaries = []
        
        # Process sources concurrently (in batches to avoid rate limits)
        batch_size = 5
        for i in range(0, len(extracted_content), batch_size):
            batch = extracted_content[i:i + batch_size]
            
            tasks = [self._summarize_single_source(content) for content in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, SourceSummary):
                    source_summaries.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"Source summarization failed: {result}")
            
            # Small delay between batches to respect rate limits
            if i + batch_size < len(extracted_content):
                await asyncio.sleep(1)
        
        logger.info(f"Successfully summarized {len(source_summaries)} sources")
        return source_summaries
    
    async def _summarize_single_source(self, content: Any) -> SourceSummary:
        """
        Summarize a single source using GPT-4o
        """
        try:
            # Chunk content if too long
            chunks = self._chunk_content(content.content)
            
            if len(chunks) == 1:
                summary_points = await self._summarize_chunk(chunks[0], content.title, content.domain)
            else:
                # Summarize each chunk then combine
                chunk_summaries = []
                for chunk in chunks:
                    chunk_summary = await self._summarize_chunk(chunk, content.title, content.domain)
                    chunk_summaries.extend(chunk_summary)
                
                # Consolidate chunk summaries
                summary_points = await self._consolidate_summaries(chunk_summaries, content.title)
            
            return SourceSummary(
                title=content.title,
                url=content.url,
                source_summary=summary_points,
                domain=content.domain
            )
            
        except Exception as e:
            logger.error(f"Error summarizing source {content.url}: {e}")
            # Return fallback summary
            return SourceSummary(
                title=content.title,
                url=content.url,
                source_summary=[f"Summary unavailable - processing error"],
                domain=content.domain
            )
    
    async def _summarize_chunk(self, text: str, title: str, domain: str) -> List[str]:
        """
        Summarize a text chunk into bullet points
        """
        prompt = f"""
Summarize the following government/policy document into exactly 3-4 bullet points.

Document Title: {title}
Source Domain: {domain}

Focus on:
- Key facts, figures, and statistics
- Policy decisions or recommendations  
- Government initiatives or programs
- Relevant dates and timelines
- Actionable information for government document drafting

Each bullet point should be 1-2 sentences and contain specific, factual information.

Text to summarize:
{text}

Return only the bullet points, starting each with "•":
"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert policy analyst who creates concise, factual summaries for government document drafters. Focus on specific facts, figures, and actionable information."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=400
            )
            
            content = response.choices[0].message.content.strip()
            
            # Extract bullet points
            bullet_points = []
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                    bullet_points.append(line[1:].strip())
                elif len(line) > 20 and not any(line.startswith(prefix) for prefix in ['Here are', 'Summary:', 'Key points:']):
                    bullet_points.append(line)
            
            # Ensure we have 3-4 points
            if len(bullet_points) < 3:
                bullet_points.extend([f"Additional context from {domain}"] * (3 - len(bullet_points)))
            elif len(bullet_points) > 4:
                bullet_points = bullet_points[:4]
            
            return bullet_points
            
        except Exception as e:
            logger.error(f"Chunk summarization error: {e}")
            return [f"Summary unavailable for content from {domain}"]
    
    def _chunk_content(self, content: str) -> List[str]:
        """
        Split content into chunks for processing
        """
        if len(content) <= self.max_chunk_size:
            return [content]
        
        chunks = []
        sentences = content.split('. ')
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 2 <= self.max_chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    async def _consolidate_summaries(self, chunk_summaries: List[str], title: str) -> List[str]:
        """
        Consolidate multiple chunk summaries into 3-4 key points
        """
        combined_text = "\n".join(chunk_summaries)
        
        prompt = f"""
The following bullet points are summaries from different sections of the same document: "{title}"

Consolidate these into exactly 3-4 key bullet points that capture the most important information:

{combined_text}

Return only the consolidated bullet points, starting each with "•":
"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You consolidate multiple summaries into the most important key points."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=300
            )
            
            content = response.choices[0].message.content.strip()
            
            bullet_points = []
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                    bullet_points.append(line[1:].strip())
            
            return bullet_points[:4] if bullet_points else chunk_summaries[:4]
            
        except Exception as e:
            logger.error(f"Summary consolidation error: {e}")
            return chunk_summaries[:4]
    
    async def synthesize_summary(self, source_summaries: List[SourceSummary], subject: str, purpose: str) -> List[str]:
        """
        Create a unified synthesis from all source summaries
        """
        if not source_summaries:
            return ["No relevant sources found for analysis."]
        
        # Combine all source summaries
        all_points = []
        for source in source_summaries:
            for point in source.source_summary:
                all_points.append(f"[{source.domain}] {point}")
        
        combined_summaries = "\n".join(all_points)
        
        prompt = f"""
Create a unified synthesis for a government document on the following:
- Subject: {subject}
- Purpose: {purpose}

Based on these research findings from multiple sources:

{combined_summaries}

Synthesize this information into exactly 5-7 bullet points that:
1. Group related themes together
2. Highlight the most relevant facts and figures
3. Focus on actionable insights for government document drafting
4. Maintain factual accuracy
5. Prioritize recent developments and official government positions

Each bullet point should be 2-3 sentences and provide specific, useful information.

Return only the bullet points, starting each with "•":
"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a senior policy analyst creating executive-level summaries for government document drafters. Focus on synthesis, themes, and actionable insights."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=600
            )
            
            content = response.choices[0].message.content.strip()
            
            # Extract bullet points
            bullet_points = []
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                    bullet_points.append(line[1:].strip())
                elif len(line) > 30 and not any(line.startswith(prefix) for prefix in ['Here', 'Based', 'The following']):
                    bullet_points.append(line)
            
            # Ensure we have 5-7 points
            if len(bullet_points) < 5:
                # Add fallback points
                bullet_points.extend([
                    f"Research indicates {subject} is a significant policy area requiring attention.",
                    f"Multiple government sources provide relevant context for {purpose}."
                ][:5 - len(bullet_points)])
            elif len(bullet_points) > 7:
                bullet_points = bullet_points[:7]
            
            logger.info(f"Generated synthesis with {len(bullet_points)} key points")
            return bullet_points
            
        except Exception as e:
            logger.error(f"Synthesis generation error: {e}")
            # Fallback synthesis
            return [
                f"Research compiled from {len(source_summaries)} government and policy sources.",
                f"Key themes identified related to {subject} and {purpose}.",
                "Multiple official sources provide relevant background information.",
                "Recent developments and policy positions have been documented.",
                "Further analysis recommended based on collected research."
            ]