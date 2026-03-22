"""
Research Analyst Agent
RAG-powered agent for answering questions about financial documents.
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from app.services.vector_service import vector_service
from app.services.llm_client import llm_client


@dataclass
class ResearchFinding:
    answer: str
    confidence: float
    sources: List[Dict[str, Any]]
    reasoning: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "confidence": self.confidence,
            "sources": self.sources,
            "reasoning": self.reasoning
        }


class ResearchAnalyst:
    """
    The 'Research' Agent (Layer 5).
    Role: Document Intelligence & Knowledge Retrieval.
    Principle: "I can find and synthesize information from your financial documents."
    """
    
    def __init__(self):
        self.name = "Research Analyst"
        self.capabilities = [
            "semantic_search",
            "document_qa",
            "fact_extraction",
            "cross_reference"
        ]
    
    @property
    def is_available(self) -> bool:
        return vector_service.is_available
    
    async def research(
        self, 
        question: str,
        context_chunks: int = 5,
        doc_filter: Optional[str] = None
    ) -> ResearchFinding:
        """
        Research a question by retrieving and synthesizing document knowledge.
        
        Args:
            question: The research question
            context_chunks: Number of relevant chunks to retrieve
            doc_filter: Optional document ID to restrict search
        """
        if not self.is_available:
            return ResearchFinding(
                answer="Research functionality unavailable - vector service not configured.",
                confidence=0.0,
                sources=[]
            )
        
        # Step 1: Retrieve relevant context
        filter_meta = {"doc_id": doc_filter} if doc_filter else None
        results = await vector_service.search(
            query=question,
            top_k=context_chunks,
            filter_metadata=filter_meta
        )
        
        if not results:
            return ResearchFinding(
                answer="No relevant information found in the document database.",
                confidence=0.0,
                sources=[]
            )
        
        # Step 2: Prepare sources
        sources = []
        context_parts = []
        
        for i, result in enumerate(results):
            context_parts.append(f"[Document Excerpt {i+1}]:\n{result.text}")
            sources.append({
                "doc_id": result.metadata.get("doc_id", "unknown"),
                "chunk": result.metadata.get("chunk_index", 0),
                "score": result.score,
                "excerpt": result.text[:200] + "..." if len(result.text) > 200 else result.text
            })
        
        context = "\n\n".join(context_parts)
        avg_score = sum(r.score for r in results) / len(results)
        
        # Step 3: Synthesize with LLM
        if llm_client.is_available:
            system_prompt = """You are a senior financial research analyst.
Your role is to accurately answer questions using ONLY the provided document excerpts.

Guidelines:
- Cite specific numbers, dates, and facts when available
- If information is incomplete, acknowledge the gaps
- Never fabricate data not present in the excerpts
- Be concise but comprehensive"""

            user_prompt = f"""Based on the following document excerpts, answer this question:

QUESTION: {question}

DOCUMENT EXCERPTS:
{context}

Provide a clear, factual answer:"""

            answer = llm_client.generate_text(system_prompt, user_prompt)
            
            if answer:
                return ResearchFinding(
                    answer=answer,
                    confidence=round(min(0.95, avg_score + 0.15), 2),
                    sources=sources,
                    reasoning=f"Synthesized from {len(results)} document excerpts"
                )
        
        # Fallback: Return best match without synthesis
        best = results[0]
        return ResearchFinding(
            answer=best.text,
            confidence=round(best.score, 2),
            sources=sources,
            reasoning="Direct excerpt (LLM synthesis unavailable)"
        )
    
    async def extract_facts(
        self, 
        topic: str,
        max_facts: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Extract key facts about a topic from documents.
        
        Args:
            topic: Topic to extract facts about (e.g., "revenue", "expenses")
            max_facts: Maximum number of facts to return
        """
        if not self.is_available:
            return []
        
        results = await vector_service.search(
            query=f"facts and figures about {topic}",
            top_k=max_facts
        )
        
        facts = []
        for result in results:
            facts.append({
                "fact": result.text[:300],
                "source_doc": result.metadata.get("doc_id", "unknown"),
                "relevance": result.score
            })
        
        return facts
    
    async def compare_documents(
        self, 
        doc_id_1: str, 
        doc_id_2: str,
        aspect: str = "revenue"
    ) -> Dict[str, Any]:
        """
        Compare two documents on a specific aspect.
        """
        if not self.is_available:
            return {"error": "Service unavailable"}
        
        # Get context from each document
        results_1 = await vector_service.search(
            query=aspect,
            top_k=3,
            filter_metadata={"doc_id": doc_id_1}
        )
        
        results_2 = await vector_service.search(
            query=aspect,
            top_k=3,
            filter_metadata={"doc_id": doc_id_2}
        )
        
        return {
            "aspect": aspect,
            "document_1": {
                "doc_id": doc_id_1,
                "findings": [r.text[:200] for r in results_1]
            },
            "document_2": {
                "doc_id": doc_id_2,
                "findings": [r.text[:200] for r in results_2]
            }
        }


# Singleton instance
research_analyst = ResearchAnalyst()
