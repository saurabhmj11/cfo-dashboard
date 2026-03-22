
import pytest
import pandas as pd
from app.services.validator import DataValidator
import os
import json

# Create sample files for testing
def create_sample_files():
    # CSV
    csv_data = {
        "date": ["2023-01-01", "2023-01-02"],
        "revenue": [1000, 2000],
        "expenses": [500, 800],
        "category": ["Sales", "Service"]
    }
    pd.DataFrame(csv_data).to_csv("test_sample.csv", index=False)

    # Excel
    pd.DataFrame(csv_data).to_excel("test_sample.xlsx", index=False)
    
    # JSON
    with open("test_sample.json", "w") as f:
        json.dump(csv_data, f)
    
    # PDF creation needs a library, mocking for now or skipping real PDF creation if reportlab is missing
    # But we can test the validator's error handling for bad PDFs
    with open("test_bad.pdf", "w") as f:
        f.write("Not a real PDF")

def test_validate_file():
    create_sample_files()
    validator = DataValidator()
    
    # Test CSV
    valid, errors = validator.validate_file("test_sample.csv", "test_sample.csv")
    assert len(valid) == 2, f"CSV failed: {errors}"
    
    # Test Excel
    valid, errors = validator.validate_file("test_sample.xlsx", "test_sample.xlsx")
    assert len(valid) == 2, f"Excel failed: {errors}"

    # Test JSON
    valid, errors = validator.validate_file("test_sample.json", "test_sample.json")
    assert len(valid) == 2, f"JSON failed: {errors}"
    
    # Test Clean Up
    if os.path.exists("test_sample.csv"): os.remove("test_sample.csv")
    if os.path.exists("test_sample.xlsx"): os.remove("test_sample.xlsx")
    if os.path.exists("test_sample.json"): os.remove("test_sample.json")
    if os.path.exists("test_bad.pdf"): os.remove("test_bad.pdf")
    
if __name__ == "__main__":
    try:
        test_validate_file()
        print("Test Passed: CSV, Excel, and JSON supported!")
    except Exception as e:
        print(f"Test Failed: {e}")
