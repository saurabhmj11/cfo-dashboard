"""
Vector Service for RAG Document Intelligence
ChromaDB-backed semantic document store for financial document retrieval.
"""
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import hashlib

# ChromaDB for vector storage
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("[VECTOR WARNING] chromadb not installed. Run: pip install chromadb")

# Sentence Transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("[VECTOR WARNING] sentence-transformers not installed. Run: pip install sentence-transformers")


@dataclass
class SearchResult:
    doc_id: str
    text: str
    score: float
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "text": self.text,
            "score": self.score,
            "metadata": self.metadata
        }


class VectorService:
    """
    ChromaDB-backed semantic document store.
    Chunks, embeds, and retrieves financial documents.
    """
    
    COLLECTION_NAME = "financial_docs"
    VECTOR_DB_PATH = "data/vectordb"
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize vector service.
        
        Args:
            model_name: Sentence transformer model for embeddings
                        - "all-MiniLM-L6-v2" (fast, 384 dims)
                        - "all-mpnet-base-v2" (better quality, 768 dims)
        """
        self._client = None
        self._collection = None
        self._model = None
        self._model_name = model_name
        
        # Ensure directory exists
        os.makedirs(self.VECTOR_DB_PATH, exist_ok=True)
    
    @property
    def is_available(self) -> bool:
        return CHROMADB_AVAILABLE and EMBEDDINGS_AVAILABLE
    
    def _get_client(self):
        """Lazy initialization of ChromaDB client."""
        if self._client is None and CHROMADB_AVAILABLE:
            self._client = chromadb.PersistentClient(
                path=self.VECTOR_DB_PATH,
                settings=Settings(anonymized_telemetry=False)
            )
        return self._client
    
    def _get_collection(self):
        """Get or create the documents collection."""
        if self._collection is None:
            client = self._get_client()
            if client:
                self._collection = client.get_or_create_collection(
                    name=self.COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"}  # Use cosine similarity
                )
        return self._collection
    
    def _get_model(self):
        """Lazy initialization of embedding model."""
        if self._model is None and EMBEDDINGS_AVAILABLE:
            print(f"[VECTOR] Loading embedding model: {self._model_name}")
            self._model = SentenceTransformer(self._model_name)
        return self._model
    
    def _generate_id(self, text: str, prefix: str = "doc") -> str:
        """Generate a unique ID for a document chunk."""
        hash_val = hashlib.md5(text.encode()).hexdigest()[:12]
        return f"{prefix}_{hash_val}"
    
    def chunk_text(
        self, 
        text: str, 
        chunk_size: int = 500, 
        overlap: int = 50
    ) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Full document text
            chunk_size: Target characters per chunk
            overlap: Overlap between chunks
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence/paragraph boundary
            if end < len(text):
                # Look for sentence end
                for sep in ['. ', '\n\n', '\n', ', ']:
                    break_point = text.rfind(sep, start + chunk_size // 2, end)
                    if break_point > start:
                        end = break_point + len(sep)
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks
    
    async def embed_document(
        self, 
        doc_id: str, 
        text: str, 
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 500
    ) -> int:
        """
        Chunk and embed a document into the vector store.
        
        Args:
            doc_id: Unique document identifier (e.g., dataset_id)
            text: Full document text
            metadata: Additional metadata (source, type, etc.)
        
        Returns:
            Number of chunks embedded
        """
        if not self.is_available:
            print("[VECTOR] Service unavailable - skipping embedding")
            return 0
        
        collection = self._get_collection()
        model = self._get_model()
        
        if not collection or not model:
            return 0
        
        # Chunk the text
        chunks = self.chunk_text(text, chunk_size=chunk_size)
        
        if not chunks:
            return 0
        
        # Generate embeddings
        embeddings = model.encode(chunks).tolist()
        
        # Prepare for ChromaDB
        ids = []
        metadatas = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{i}"
            ids.append(chunk_id)
            
            chunk_meta = {
                "doc_id": doc_id,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "text_preview": chunk[:100] + "..." if len(chunk) > 100 else chunk,
                **(metadata or {})
            }
            metadatas.append(chunk_meta)
        
        # Upsert into collection
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas
        )
        
        print(f"[VECTOR] Embedded {len(chunks)} chunks for doc '{doc_id}'")
        return len(chunks)
    
    async def search(
        self, 
        query: str, 
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Semantic search over embedded documents.
        
        Args:
            query: Natural language search query
            top_k: Number of results to return
            filter_metadata: Optional metadata filter
        
        Returns:
            List of SearchResult objects
        """
        if not self.is_available:
            return []
        
        collection = self._get_collection()
        model = self._get_model()
        
        if not collection or not model:
            return []
        
        # Embed query
        query_embedding = model.encode([query])[0].tolist()
        
        # Search
        where_filter = filter_metadata if filter_metadata else None
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        
        # Convert to SearchResult objects
        search_results = []
        
        if results and results['ids'] and results['ids'][0]:
            for i, doc_id in enumerate(results['ids'][0]):
                # ChromaDB returns distances - convert to similarity score
                distance = results['distances'][0][i] if results['distances'] else 0
                score = 1 - distance  # Cosine distance to similarity
                
                search_results.append(SearchResult(
                    doc_id=doc_id,
                    text=results['documents'][0][i] if results['documents'] else "",
                    score=round(score, 4),
                    metadata=results['metadatas'][0][i] if results['metadatas'] else {}
                ))
        
        return search_results
    
    async def delete_document(self, doc_id: str) -> bool:
        """Delete all chunks for a document."""
        if not self.is_available:
            return False
        
        collection = self._get_collection()
        if not collection:
            return False
        
        try:
            # Get all chunks for this document
            results = collection.get(
                where={"doc_id": doc_id},
                include=[]
            )
            
            if results['ids']:
                collection.delete(ids=results['ids'])
                print(f"[VECTOR] Deleted {len(results['ids'])} chunks for doc '{doc_id}'")
                return True
            
            return False
            
        except Exception as e:
            print(f"[VECTOR ERROR] Failed to delete doc '{doc_id}': {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        if not self.is_available:
            return {"available": False}
        
        collection = self._get_collection()
        if not collection:
            return {"available": False}
        
        return {
            "available": True,
            "total_chunks": collection.count(),
            "collection_name": self.COLLECTION_NAME,
            "embedding_model": self._model_name
        }


# Singleton instance
vector_service = VectorService()
