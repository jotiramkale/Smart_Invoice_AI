import os
import json
import pandas as pd

from dotenv import load_dotenv
from groq import Groq
from pypdf import PdfReader
from paddleocr import PaddleOCR


# Load API key
load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

# OCR model
ocr = PaddleOCR(lang="en")


# Extract text from PDF or Image
def extract_text(file_path):

    if file_path.endswith(".pdf"):

        reader = PdfReader(file_path)

        text = ""

        for page in reader.pages:
            if page.extract_text():
                text += page.extract_text()

        return text

    else:

        result = ocr.ocr(file_path)

        text = ""

        for line in result:
            for word in line:
                text += word[1][0] + " "

        return text


# Send text to Groq and get invoice data
def extract_invoice_json(text):

    prompt = f"""
Extract invoice details and return JSON only.

Format:

{{
    "invoice_number":"",
    "invoice_date":"",
    "vendor":"",
    "customer":"",
    "subtotal":"",
    "tax":"",
    "total":"",
    "items":[
        {{
            "item":"",
            "quantity":"",
            "amount":""
        }}
    ]
}}

Invoice Text:

{text}
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content


# Convert JSON string to Python dictionary
def parse_json(response):

    response = response.replace("```json", "")
    response = response.replace("```", "")

    return json.loads(response)


# Save Excel file
def export_excel(data, file_name="invoice_output.xlsx"):

    summary = pd.DataFrame([
        {
            "Invoice Number": data.get("invoice_number", ""),
            "Invoice Date": data.get("invoice_date", ""),
            "Vendor": data.get("vendor", ""),
            "Customer": data.get("customer", ""),
            "Subtotal": data.get("subtotal", ""),
            "Tax": data.get("tax", ""),
            "Total": data.get("total", "")
        }
    ])

    items = pd.DataFrame(data.get("items", []))

    with pd.ExcelWriter(file_name) as writer:

        summary.to_excel(
            writer,
            sheet_name="Invoice Summary",
            index=False
        )

        items.to_excel(
            writer,
            sheet_name="Invoice Items",
            index=False
        )

    return file_name