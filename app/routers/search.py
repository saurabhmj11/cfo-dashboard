"""
Search Router for RAG Document Intelligence
Semantic search and Q&A over financial documents.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from app.services.vector_service import vector_service
from app.services.llm_client import llm_client
from app.dependencies import get_current_user
from app.models.db_models import User

router = APIRouter(
    prefix="/api/v1/search",
    tags=["search"]
)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query")
    top_k: int = Field(5, ge=1, le=20, description="Number of results")
    doc_id: Optional[str] = Field(None, description="Filter by document ID")


class AskRequest(BaseModel):
    question: str = Field(..., min_length=5, description="Question to answer")
    top_k: int = Field(3, ge=1, le=10, description="Context chunks to retrieve")


@router.get("/status")
async def get_search_status():
    """Get vector service status."""
    return vector_service.get_stats()


@router.post("/")
async def semantic_search(
    request: SearchRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Perform semantic search over embedded documents.
    
    Example: POST /api/v1/search
    {
        "query": "What are the total operating expenses?",
        "top_k": 5
    }
    """
    if not vector_service.is_available:
        raise HTTPException(
            status_code=503,
            detail="Vector service unavailable. Install chromadb & sentence-transformers."
        )
    
    # Build filter if doc_id provided
    filter_metadata = {"doc_id": request.doc_id} if request.doc_id else None
    
    results = await vector_service.search(
        query=request.query,
        top_k=request.top_k,
        filter_metadata=filter_metadata
    )
    
    return {
        "status": "success",
        "query": request.query,
        "count": len(results),
        "results": [r.to_dict() for r in results]
    }


@router.post("/ask")
async def ask_question(
    request: AskRequest,
    current_user: User = Depends(get_current_user)
):
    """
    RAG-powered Q&A: Retrieve relevant chunks and answer using LLM.
    
    Example: POST /api/v1/search/ask
    {
        "question": "What is the company's total revenue?",
        "top_k": 3
    }
    """
    if not vector_service.is_available:
        raise HTTPException(
            status_code=503,
            detail="Vector service unavailable."
        )
    
    # Step 1: Retrieve relevant context
    results = await vector_service.search(
        query=request.question,
        top_k=request.top_k
    )
    
    if not results:
        return {
            "status": "success",
            "answer": "I couldn't find any relevant information in the uploaded documents.",
            "sources": [],
            "confidence": 0.0
        }
    
    # Step 2: Build context from retrieved chunks
    context_parts = []
    sources = []
    
    for i, result in enumerate(results):
        context_parts.append(f"[Source {i+1}]: {result.text}")
        sources.append({
            "doc_id": result.metadata.get("doc_id", "unknown"),
            "chunk_index": result.metadata.get("chunk_index", 0),
            "relevance_score": result.score,
            "preview": result.text[:150] + "..." if len(result.text) > 150 else result.text
        })
    
    context = "\n\n".join(context_parts)
    
    # Step 3: Generate answer with LLM
    if llm_client.is_available:
        system_prompt = """You are a financial analyst assistant. 
Answer the user's question based ONLY on the provided context from financial documents.
If the context doesn't contain enough information, say so.
Be precise and cite specific numbers when available.
Format your answer clearly."""

        user_prompt = f"""Context from documents:
{context}

Question: {request.question}

Answer based on the context above:"""

        answer = llm_client.generate_text(system_prompt, user_prompt)
        
        if answer:
            # Calculate confidence based on relevance scores
            avg_score = sum(r.score for r in results) / len(results)
            confidence = round(min(0.95, avg_score + 0.2), 2)  # Boost slightly for matching
            
            return {
                "status": "success",
                "answer": answer,
                "sources": sources,
                "confidence": confidence
            }
    
    # Fallback: Return top result as answer
    best_result = results[0]
    return {
        "status": "success",
        "answer": f"Based on the documents: {best_result.text}",
        "sources": sources,
        "confidence": round(best_result.score, 2),
        "note": "LLM unavailable - showing most relevant passage"
    }


@router.delete("/document/{doc_id}")
async def delete_document_embeddings(
    doc_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete all embeddings for a document."""
    if not vector_service.is_available:
        raise HTTPException(status_code=503, detail="Vector service unavailable")
    
    success = await vector_service.delete_document(doc_id)
    
    if success:
        return {"status": "success", "message": f"Deleted embeddings for '{doc_id}'"}
    
    return {"status": "not_found", "message": f"No embeddings found for '{doc_id}'"}
