import os
import json
import pandas as pd
from flask import Flask, render_template, request, send_file

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
ocr = None


# Extract text from PDF or Image
def extract_text(file_path):

    global ocr

    if file_path.endswith(".pdf"):

        reader = PdfReader(file_path)

        text = ""

        for page in reader.pages:
            if page.extract_text():
                text += page.extract_text()

        return text

    else:

        if ocr is None:
            ocr = PaddleOCR(lang="en")

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


# Flask application setup
app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
EXCEL_FILE = os.path.join(UPLOAD_FOLDER, "invoice_output.xlsx")
ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(file_name):
    return "." in file_name and file_name.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET", "POST"])
def index():
    data = None
    error = None

    if request.method == "POST":
        uploaded_file = request.files.get("invoice")

        if uploaded_file is None or uploaded_file.filename == "":
            error = "Please choose an invoice file."
        elif not allowed_file(uploaded_file.filename):
            error = "Please upload a PDF, JPG, JPEG, or PNG file."
        else:
            file_name = uploaded_file.filename
            file_path = os.path.join(UPLOAD_FOLDER, file_name)

            try:
                uploaded_file.save(file_path)
                text = extract_text(file_path)
                response = extract_invoice_json(text)
                data = parse_json(response)
                export_excel(data, EXCEL_FILE)
            except Exception as exception:
                error = str(exception)
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

    return render_template("index.html", data=data, error=error)


@app.route("/download")
def download_excel():
    if not os.path.exists(EXCEL_FILE):
        return "Analyze an invoice before downloading Excel.", 404

    return send_file(EXCEL_FILE, as_attachment=True, download_name="invoice_output.xlsx")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)