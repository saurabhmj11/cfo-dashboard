import pdfplumber
import json
import pandas as pd
from datetime import datetime
import re
from typing import List, Dict, Any
import os
import asyncio
from app.database import SessionLocal
from app.models.db_models import Dataset, Transaction

class RefineryService:
    """
    Phase 1.5: The Data Refinery.
    Ingests "Raw/Messy" documents and refines them into "Golden" data.
    """
    
    def process_pdf(self, file_path: str, dataset_id: int):
        """
        Background Task:
        1. Extract text/tables from PDF.
        2. Parse using Heuristics (Regex).
        3. Save to DB.
        4. Generate Golden Excel.
        """
        print(f"Refinery: Starting process for {file_path}")
        
        extracted_data = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        lines = text.split('\n')
                        for line in lines:
                            parsed_line = self._parse_bank_line(line)
                            if parsed_line:
                                extracted_data.append(parsed_line)
        except Exception as e:
            print(f"Refinery Error: {str(e)}")
            # In production, update Dataset status to FAILED
            return

        if not extracted_data:
            print("Refinery: No valid transactions found.")
            return

        # Convert to DataFrame
        df = pd.DataFrame(extracted_data)
        
        # Save to DB
        db = SessionLocal()
        try:
            # 1. Update Dataset
            dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
            if dataset:
                dataset.row_count = len(df)
                dataset.is_golden = 1 # Mark as processed
            
            # 2. Insert Transactions
            for _, row in df.iterrows():
                txn = Transaction(
                    dataset_id=dataset_id,
                    txn_date=datetime.strptime(row['date'], "%Y-%m-%d").date(),
                    revenue=float(row['credit']),
                    expenses=float(row['debit']),
                    category=row['description']
                )
                db.add(txn)
            
            db.commit()
            print(f"Refinery: Saved {len(df)} txns to DB.")
            
            output_path = file_path.replace(".pdf", "_golden.xlsx")
            df.to_excel(output_path, index=False)
            print(f"Refinery: Generated Golden Excel at {output_path}")
            
            # RAG: Embed extracted text for semantic search
            self._embed_document_async(dataset_id, file_path)

        except Exception as ex:
            print(f"DB Error: {ex}")
            db.rollback()
        finally:
            db.close()

    def process_json(self, file_path: str, dataset_id: int):
        """
        Background Task for JSON:
        1. Parse JSON list.
        2. Map fields to Schema.
        3. Save to DB.
        4. Generate Golden Excel.
        """
        print(f"Refinery: Starting JSON process for {file_path}")
        
        extracted_data = []
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            # Smart unwrapping
            if isinstance(data, dict):
                for key in ["transactions", "data", "items", "records", "rows"]:
                    if key in data and isinstance(data[key], list):
                        data = data[key]
                        break
            
            if not isinstance(data, list):
                print(f"Refinery JSON Error: Data is {type(data)}, expected list.")
                # Fallback: if it's a single dict, wrap in list
                if isinstance(data, dict):
                    data = [data]
                else:
                    return

            for item in data:
                # Heuristic Mapping
                txn = {}
                
                # 1. Date (Crucial)
                date_str = None
                for k in ["date", "txn_date", "timestamp", "created_at", "day", "time"]:
                    if k in item and item[k]:
                        date_str = str(item[k])
                        break
                
                if not date_str: 
                    # Last resort fallback: Today
                    date_str = datetime.now().strftime("%Y-%m-%d")
                
                # Normalize Date
                try:
                    if "T" in date_str: date_str = date_str.split("T")[0]
                    # Validate format
                    pd.to_datetime(date_str) # Check if pandas accepts it
                    txn["date"] = date_str 
                except:
                    txn["date"] = datetime.now().strftime("%Y-%m-%d")

                # 2. Description
                desc = "Unknown Transaction"
                for k in ["description", "desc", "details", "memo", "text", "label", "narrative"]:
                    if k in item and item[k]:
                        desc = str(item[k])
                        break
                txn["description"] = desc[:100]
                
                # 3. Amount (Credit/Debit logic)
                credit = 0.0
                debit = 0.0
                
                # Check explicit credit/debit keys first
                c_val = item.get("credit") or item.get("deposit") or item.get("income")
                d_val = item.get("debit") or item.get("withdrawal") or item.get("expense")
                
                if c_val is not None: credit = float(c_val)
                if d_val is not None: debit = float(d_val)
                
                # If neither, check generic 'amount'
                if credit == 0 and debit == 0:
                    amt_val = item.get("amount") or item.get("value") or item.get("cost") or item.get("total")
                    if amt_val is not None:
                        try:
                            val = float(amt_val)
                            if val >= 0:
                                credit = val
                            else:
                                debit = abs(val)
                        except:
                            pass
                            
                txn["credit"] = credit
                txn["debit"] = debit
                
                # 4. Category (Optional)
                txn["category"] = item.get("category") or "Uncategorized"

                extracted_data.append(txn)

        except Exception as e:
            print(f"Refinery JSON Error: {str(e)}")
            return

        if not extracted_data:
            print("Refinery JSON: No valid transactions extracted.")
            return

        # Create DataFrame with explicit schema
        df = pd.DataFrame(extracted_data)
        
        # Ensure all columns exist
        required_cols = ["date", "description", "credit", "debit", "category"]
        for col in required_cols:
            if col not in df.columns:
                df[col] = "" if col == "category" else 0.0
        
        # Reorder
        df = df[required_cols]

        # Save to DB
        db = SessionLocal()
        try:
            dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
            if dataset:
                dataset.row_count = len(df)
                dataset.is_golden = 1
            
            for _, row in df.iterrows():
                try:
                    d_obj = pd.to_datetime(row['date']).date()
                except:
                    d_obj = datetime.now().date()

                txn = Transaction(
                    dataset_id=dataset_id,
                    txn_date=d_obj,
                    revenue=float(row['credit']),
                    expenses=float(row['debit']),
                    category=str(row['category'])
                )
                db.add(txn)
            
            db.commit()
            print(f"Refinery JSON: Saved {len(df)} txns to DB.")
            
            output_path = file_path.replace(".json", "_golden.xlsx")
            df.to_excel(output_path, index=False)
            print(f"Refinery: Generated Golden Excel at {output_path}")
            
        except Exception as ex:
            print(f"DB Error: {ex}")
            db.rollback()
        finally:
            db.close()
            
        # RAG: Embed JSON content for semantic search
        self._embed_document_async(dataset_id, file_path)

    def _parse_bank_line(self, line: str) -> Dict[str, Any]:
        """
        Heuristic: Looks for Date (YYYY-MM-DD or MM/DD/YYYY) + Amount.
        Very basic implementation for MVP.
        """
        # Regex for Date (DD/MM/YYYY or YYYY-MM-DD)
        date_pattern = r"(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})"
        match = re.search(date_pattern, line)
        
        if not match:
            return None
            
        date_str = match.group(1)
        
        # Try to parse date
        try:
            # Normalize to YYYY-MM-DD
            if "/" in date_str:
                dt = datetime.strptime(date_str, "%m/%d/%Y")
            else:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            formatted_date = dt.strftime("%Y-%m-%d")
        except:
            return None

        # Extract amounts (looking for numbers with decimals)
        # Strategy: Last number in line is likely balance, second last is amount? 
        # Simplified: Look for any number. Positive = Credit, Negative = Debit?
        # Better: Just find all numbers.
        numbers = re.findall(r"[-+]?\d*\.\d+|\d+", line)
        clean_nums = []
        for n in numbers:
            try:
                if "." in n: clean_nums.append(float(n))
            except: pass
            
        if not clean_nums:
            return None
            
        amount = clean_nums[-1] # Assume last number is amount
        
        # Determine Debit/Credit (Naive)
        # If "Cr" in line or "Deposit", it's credit.
        is_credit = "deposit" in line.lower() or "cr" in line.lower() or "credit" in line.lower()
        
        # Description is the rest
        desc = line.replace(date_str, "").replace(str(amount), "").strip()
        
        return {
            "date": formatted_date,
            "description": desc[:50], # Truncate
            "credit": amount if is_credit else 0.0,
            "debit": 0.0 if is_credit else amount
        }
    
    def _embed_document_async(self, dataset_id: int, file_path: str):
        """
        Extract text from document and embed for RAG semantic search.
        Runs asynchronously to avoid blocking.
        """
        try:
            from app.services.vector_service import vector_service
            
            if not vector_service.is_available:
                print("[REFINERY] Vector service unavailable - skipping embedding")
                return
            
            # Extract full text based on file type
            full_text = ""
            
            if file_path.endswith(".pdf"):
                try:
                    with pdfplumber.open(file_path) as pdf:
                        for page in pdf.pages:
                            text = page.extract_text()
                            if text:
                                full_text += text + "\n\n"
                except Exception as e:
                    print(f"[REFINERY] PDF text extraction failed: {e}")
                    return
                    
            elif file_path.endswith(".json"):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    # Convert JSON to readable text
                    full_text = json.dumps(data, indent=2)
                except Exception as e:
                    print(f"[REFINERY] JSON read failed: {e}")
                    return
            
            if not full_text or len(full_text) < 50:
                print("[REFINERY] Not enough text to embed")
                return
            
            # Embed asynchronously
            async def do_embed():
                count = await vector_service.embed_document(
                    doc_id=str(dataset_id),
                    text=full_text,
                    metadata={
                        "source_file": os.path.basename(file_path),
                        "file_type": "pdf" if file_path.endswith(".pdf") else "json"
                    },
                    chunk_size=500
                )
                print(f"[REFINERY] Embedded {count} chunks for dataset {dataset_id}")
            
            # Run in new event loop (since we're in a sync context)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(do_embed())
                else:
                    asyncio.run(do_embed())
            except RuntimeError:
                # No event loop, create one
                asyncio.run(do_embed())
                
        except Exception as e:
            print(f"[REFINERY] Embedding failed: {e}")

refinery_service = RefineryService()

