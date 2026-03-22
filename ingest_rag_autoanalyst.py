import sys
import os
import asyncio

# Add current project root to sys.path
# This script should be run from f:\product\dashboard\financial_analyst
sys.path.append(os.getcwd())

# Mock st.session_state if needed or any streamlit imports in AutoAnalyst
# Actually, we just want to read the files, not run them.
# Our VectorService just needs the text.

from app.services.vector_service import vector_service

async def ingest_autoanalyst():
    print("Starting RAG ingestion for AutoAnalyst-AI...")
    
    source_dir = r"F:\product\AutoAnalyst-AI-main\AutoAnalyst-AI-main"
    files_to_ingest = [
        "nl2sql.py",
        "eda.py",
        "data_cleaning.py",
        "automl.py"
    ]
    
    if not vector_service.is_available:
        print("Vector service is not available. Check chromadb and sentence-transformers installation.")
        return

    for filename in files_to_ingest:
        file_path = os.path.join(source_dir, filename)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            print(f"Embedding {filename}...")
            # Use doc_id as the filename for easy reference
            chunks = await vector_service.embed_document(
                doc_id=f"skill_{filename}",
                text=content,
                metadata={
                    "source": "autoanalyst_ai",
                    "type": "skill_template",
                    "module": filename,
                    "description": f"Expert logic for {filename} from the AutoAnalyst-AI ecosystem."
                }
            )
            print(f"Successfully embedded {chunks} chunks for {filename}.")
        else:
            print(f"Warning: {file_path} not found.")

    print("RAG Ingestion Complete.")

if __name__ == "__main__":
    asyncio.run(ingest_autoanalyst())
