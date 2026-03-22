import pandas as pd
from typing import List, Tuple, Dict, Any
from pydantic import BaseModel, Field, field_validator, ValidationError
from datetime import date, datetime
import numpy as np

# --- Layer 1: Strict Schema Definition ---
class RawTransaction(BaseModel):
    """
    Represents a single row from the raw CSV.
    Enforces types and business rules immediately upon ingestion.
    """
    date: date
    revenue: float = Field(..., ge=0)
    expenses: float = Field(..., ge=0)
    category: str = Field(default="Uncategorized")
    description: str = Field(default="")
    
    @field_validator('date', mode='before')
    def parse_date(cls, v):
        if isinstance(v, (datetime, date)):
            return v
        if isinstance(v, str):
            try:
                return pd.to_datetime(v).date()
            except:
                raise ValueError(f"Invalid date format: {v}")
        raise ValueError("Date missing or invalid type")

    @field_validator('revenue', 'expenses', mode='before')
    def clean_currency(cls, v):
        if isinstance(v, str):
            # Remove currency symbols and commas
            clean_str = v.replace('$', '').replace('₹', '').replace(',', '').strip()
            if not clean_str: return 0.0
            return float(clean_str)
        if isinstance(v, (int, float)):
            return float(v)
        return 0.0

# --- Layer 1: Validation Service ---
class DataValidator:
    """
    The Gatekeeper.
    Responsibilities:
    1. Read Raw Buffer
    2. Enforce Pydantic Schema
    3. Return 'Golden' records or Reject
    """
    
    def validate_file(self, file_path: str, filename: str) -> Tuple[List[RawTransaction], List[str]]:
        """
        Reads CSV, Excel, or PDF and validates every row.
        Returns: (Valid Records, List of Error Messages)
        """
        try:
            ext = filename.lower().split('.')[-1]
            if ext == 'csv':
                df = pd.read_csv(file_path)
            elif ext in ['xlsx', 'xls']:
                df = pd.read_excel(file_path)
            elif ext == 'pdf':
                import pdfplumber
                data = []
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        table = page.extract_table()
                        if table:
                            # Assume first row is header if data is empty
                            if not data:
                                headers = table[0]
                                rows = table[1:]
                            else:
                                rows = table
                            data.extend(rows)
                
                if not data:
                    return [], ["PDF Error: No tabular data found. Ensure the PDF contains a clear table."]
                
                df = pd.DataFrame(data, columns=headers)
            elif ext == 'json':
                df = pd.read_json(file_path)
            else:
                return [], [f"Unsupported file format: {ext}"]

            # Normalize Headers: lowercase, strip
            df.columns = [str(c).lower().strip() for c in df.columns]
            
            # Map common variations to canonical names
            header_map = {
                'rev': 'revenue', 'inc': 'revenue', 'income': 'revenue',
                'exp': 'expenses', 'cost': 'expenses',
                'cat': 'category', 'type': 'category',
                'dt': 'date', 'day': 'date',
                'transaction date': 'date', 'txn date': 'date'
            }
            df.rename(columns=header_map, inplace=True)
            
            # Check required columns
            required = {'date', 'revenue', 'expenses'}
            missing = required - set(df.columns)
            if missing:
                return [], [f"Critical Schema Error: Missing columns {missing}"]
            
        except ImportError as e:
             return [], [f"Server Error: Missing dependency for {ext} files. Contact admin."]
        except Exception as e:
            return [], [f"File Read Error: {str(e)}"]

        valid_records = []
        errors = []

        # Row-by-Row Strict Validation
        for idx, row in df.iterrows():
            try:
                # Convert row to dict, handling NaNs
                row_dict = row.where(pd.notnull(row), None).to_dict()
                
                # Pydantic Parse
                txn = RawTransaction(**row_dict)
                valid_records.append(txn)
                
            except ValidationError as e:
                # Capture specific field errors
                for err in e.errors():
                    loc = err.get('loc', ('unknown',))
                    msg = err.get('msg', 'Invalid')
                    errors.append(f"Row {idx+2}: Field '{loc[0]}' - {msg}")
            except Exception as e:
                errors.append(f"Row {idx+2}: Unexpected error - {str(e)}")

        return valid_records, errors
