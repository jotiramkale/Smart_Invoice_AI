import os
import tempfile
import streamlit as st

from app import extract_text, extract_invoice_json, parse_json, export_excel

st.title("SmartInvoice AI")

uploaded_file = st.file_uploader(
    "Upload Invoice",
    type=["pdf", "jpg", "jpeg", "png"]
)

if st.button("Analyze Invoice"):

    if uploaded_file is None:
        st.error("Please upload a file")

    else:

        try:

            st.write("Processing...")

            # Save uploaded file
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=os.path.splitext(uploaded_file.name)[1]
            )

            temp_file.write(uploaded_file.getvalue())
            temp_file.close()

            # Extract invoice data
            text = extract_text(temp_file.name)

            response = extract_invoice_json(text)

            data = parse_json(response)

            # Show summary
            st.subheader("Invoice Summary")

            st.table({
                "Field": [
                    "Invoice Number",
                    "Invoice Date",
                    "Vendor",
                    "Customer",
                    "Subtotal",
                    "Tax",
                    "Total"
                ],
                "Value": [
                    data.get("invoice_number", ""),
                    data.get("invoice_date", ""),
                    data.get("vendor", ""),
                    data.get("customer", ""),
                    data.get("subtotal", ""),
                    data.get("tax", ""),
                    data.get("total", "")
                ]
            })

            # Show items
            st.subheader("Items")

            if data.get("items"):
                st.table(data["items"])
            else:
                st.write("No items found")

            # Create Excel
            excel_file = "invoice_output.xlsx"

            export_excel(data, excel_file)

            with open(excel_file, "rb") as f:

                st.download_button(
                    "Download Excel",
                    data=f,
                    file_name="invoice_output.xlsx"
                )

            os.remove(temp_file.name)

        except Exception as e:
            st.error(str(e))