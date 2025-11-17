
#File which is running in server(as on 13th August 2025)

import os
import pandas as pd
from flask import Flask, request, send_file, jsonify
from reportlab.lib.pagesizes import A4
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
from num2words import num2words
from flask_cors import CORS
from reportlab.platypus import Table, TableStyle, Image
import math
import zipfile
from reportlab.platypus import Table, TableStyle
from datetime import datetime, timedelta
import mimetypes
from flask import make_response
import uuid
import threading
from reportlab.pdfgen import canvas
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)




# Absolute folder paths based on current file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
PDF_FOLDER = os.path.join(BASE_DIR, "pdfs")
ZIP_PATH = os.path.join(PDF_FOLDER, "all_payslips.zip")
LOGO_PATH = os.path.join(BASE_DIR, "logo1.png")


# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)


import requests
import json
import base64
import mimetypes

# Constants
authkey = "450557Amsu5FsTi686518eeP1"  # Keep it secret
sender_email = "hr@operations.autoproins.com"
# recipient_email = "uma08cse49@gmail.com"
domain = "operations.autoproins.com"
template_id = "template_03_07_2025_16_07_4"

def send_email_with_attachment(recipient_email, name, pdf_path,cc_emails=None):

    cc_emails = ["shankarstatistician@gmail.com"]   # you can add multiple emails here
    # Encode PDF in base64
    with open(pdf_path, "rb") as f:
        encoded_pdf = base64.b64encode(f.read()).decode('utf-8')

    # Get file MIME type (default to application/pdf)
    mime_type, _ = mimetypes.guess_type(pdf_path)
    if not mime_type:
        mime_type = "application/pdf"

     # Dynamic month and year
    month_year = datetime.now().strftime("%B %Y")
     # Dynamic month and year
    month_name = datetime.now().strftime("%B")


    # Build payload
    payload = {
        "recipients": [
            {
                "to": [
                    {
                        "name": name,
                        "email": recipient_email
                    }
                ],
                "variables": {
                    "name": name,
                    "month_name":month_name,
                    "month_year":month_year
                },
                "cc": [{"email": email} for email in cc_emails]  # 👈 Always CC HR
            }
        ],
        
        "from": {
            "name": "HR",
            "email": sender_email
        },
        "domain": domain,
        "attachments": [
            {
                "file": f"data:{mime_type};base64,{encoded_pdf}",
                "fileName": "Payslip.pdf"
            }
        ],
        "template_id": template_id
    }

    headers = {
        "authkey": authkey,
        "content-type": "application/json",
        "accept": "application/json"
    }

    response = requests.post("https://api.msg91.com/api/v5/email/send", headers=headers, data=json.dumps(payload))

    print("Status:", response.status_code)
    try:
        print("Response:", response.json())
    except Exception as e:
        print("Error parsing response:", str(e))



# 👇 add this global variable at the top of your file
last_uploaded_file = None


# ---------------------------
# 📂 Upload Excel File
# ---------------------------
@app.route("/upload", methods=["POST"])
def upload_file():
    global last_uploaded_file

    if "file" not in request.files:
        return "No file part", 400

    file = request.files["file"]
    if file.filename == "":
        return "No selected file", 400

    # Save uploaded Excel file
    filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
    # file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file_path = os.path.join(UPLOAD_FOLDER,filename)
    file.save(file_path)

    # Remember last uploaded file
    last_uploaded_file = file_path
    print("### Uploaded Excel saved as:", last_uploaded_file)

    return "File uploaded successfully", 200


# # Logo (optional)
logo_path = "logo1.png"  # <-- Change this if your logo has a different name/path

def safe_int(value, default=0):
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default

def safe_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def generate_payslip(data, filename):
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph


    styles = getSampleStyleSheet()
    styleN = styles["Normal"]


    pdf_filename = f"{uuid.uuid4().hex}_{row['name']}.pdf"
    # pdf_path = os.path.join(PDF_FOLDER, filename)
    pdf_path = os.path.join(PDF_FOLDER, pdf_filename)
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter

    # Header text first (shifted lower)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(140, height - 60, "Auto Pro Inspection Services")
    c.setFont("Helvetica", 10)
    c.drawString(140, height - 75, "House No: 13 & 14, First Flr., Sunrise House, Czech Colony, Hyderabad - 500 018")
    # prev_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%B-%Y')
    today = datetime.now().strftime("%d-%m-%Y")
    prev_month = datetime.now().replace(day=1) - timedelta(days=1)
    month_name1 = prev_month.strftime('%B')
    year = prev_month.year
    last_day = prev_month.day
    month_year1 = prev_month.strftime('%B-%Y')
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, height - 120, f"Salary slip for the month of {month_year1}")

    # Draw logo below text, aligned left
    if os.path.exists(LOGO_PATH):
        try:
            c.drawImage(LOGO_PATH, 50, height - 90, width=50, height=50, preserveAspectRatio=True)
        except:
            pass

    # Set Y below header block
    #  start_y = height - 170

    start_y = height - 170

     # Set Y below header block
    print("Data keys on server:", list(data.keys()))
    print("Raw location value:", data.get("location"), data.get("Location"))

    loc = data.get("location") or data.get("Location") or ""
    location_str = str(loc) if pd.notna(loc) and str(loc).strip().lower() != "nan" else "N/A"

    emp_table=[
        ["Valuator Name", "Deparment", "Valuator ID", "Location", "Pay Period"],
        [
            str(data.get("valuator name", "N/A")),
            str(data.get("department", "INSPECTION")),
            str(data.get("valuator id", "N/A")).upper(),
            location_str,
            f"01 {month_name1} to {last_day} {month_name1} {year}"
        ]
    ]

    # etable = Table(emp_table, colWidths=[120, 160, 130, 90])
    etable = Table(emp_table, colWidths=[120, 100, 80, 80, 150])
    etable.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONT', (0, 0), (-1, -1), 'Helvetica', 9),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONT', (0, 1), (-1, -1), 'Helvetica'),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),             # Center-align values
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    etable.wrapOn(c, width, height)
    etable.drawOn(c, 50, start_y)



    # Adjust y position for next table
    row_height = 20
    gap_after_table = 250
    y = start_y - (len(emp_table) * row_height + gap_after_table)

    # Extract earnings and deduction values
    asset_qty = safe_int(data.get("asset verification"))
    asset_rate = safe_float(data.get("asset verification.1"))
    repo_qty = safe_int(data.get("repo"))
    repo_rate = safe_float(data.get("repo.1"))
    retail_qty = safe_int(data.get("retail"))
    retail_rate = safe_float(data.get("retail.1"))
    pi_qty = safe_int(data.get("pi case"))
    pi_rate = safe_float(data.get("pi case.1"))
    convences = safe_float(data.get("conveyances"))
    print("Convences....",convences)
    print("Available keys in data:", data.keys())

    pi_coll = safe_float(data.get("pi cases coll (pi case)"))
    cash = safe_float(data.get("valuation collection (cash)"))
    qr_diff = safe_float(data.get("(dqr diff) qr code difference"))
    advance=safe_float(data.get("advance"))
    print("Advance....",advance)

    total_earnings = asset_qty * asset_rate + repo_qty * repo_rate + retail_qty * retail_rate + pi_qty * pi_rate + convences
    total_deductions = pi_coll + cash + qr_diff + advance
    net_salary = total_earnings - total_deductions


    try:
        words = num2words(net_salary, lang='en_IN').title()
    except:
        words = "Zero"


    Arrears = safe_float(data.get("arrears"))
    Adjustment = safe_float(data.get("adjustment"))
    Amount = total_earnings + Arrears - total_deductions + Adjustment

    TotalPayable=total_earnings-total_deductions

    transfer_data = [
    ["Account No.", "Total Earnings", "Deductions", "Total Payable"],
    [
        str(data.get("account no", "N/A")),
        f"{total_earnings:,.2f} -",
        f"{total_deductions:,.2f} =",
        TotalPayable,
    ]
]

    ttable = Table(transfer_data, colWidths=[130, 130, 130,140])
    ttable.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONT', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    ttable.wrapOn(c, width, height)
    transfer_y = start_y - (len(emp_table) * 20)
    ttable.drawOn(c, 50, transfer_y)

     # Adjust y position for next table
    row_height = 20
    gap_after_table = 250
    y =  transfer_y  - (len(transfer_data) * row_height + gap_after_table)

    # Table for earnings and deductions
    earnings_data = [
        ["Component", "No of Cases", "Amount Per Case", "Total Amount"],
        ["Asset Verification", asset_qty, f"{asset_rate:.2f}", f"{asset_qty * asset_rate:.2f}"],
        ["Retail", retail_qty, f"{retail_rate:.2f}", f"{retail_qty * retail_rate:.2f}"],
        ["Repo", repo_qty, f"{repo_rate:.2f}", f"{repo_qty * repo_rate:.2f}"],
        ["PI", pi_qty, f"{pi_rate:.2f}", f"{pi_qty * pi_rate:.2f}"],
        ["Conveyance", "-", "-", f"{convences:.2f}"],
        ["Total Earnings", "", "", f"{total_earnings:.2f}"],
        ["", "", "", ""],
        ["Deductions", "", "", ""],
        ["Valuation Coll (Cash)", "", "",f"{cash:.2f}"],
        ["PI Cases Coll(PI Case)", "", "", f"{pi_coll:.2f}"],
        ["QR code Difference", "", "", f"{qr_diff:.2f}"],
        ["Advance","", "", f"{advance:.2f}"],    
        ["Total Deductions", "", "", f"{total_deductions:.2f}"],
        ["Net Salary", "", "", f"{net_salary:.2f}"],
        ["Amount in Words: " , f"{words} Rupees", "", ""]

    ]

    earnings_table = Table(earnings_data, colWidths=[160, 100, 140, 130])

    earnings_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONT', (0, 1), (-1, -1), 'Helvetica'),
        ('FONT', (0, 6), (-1, 6), 'Helvetica-Bold'),
        ('SPAN', (0, 6), (2, 6)),
        ('ALIGN', (0, 6), (2, 6), 'CENTER'),
        ('SPAN', (0, 6), (2, 6)),
        ('FONT', (0, 7), (-1, 7), 'Helvetica-Bold'),
        ('SPAN', (0, 7), (3, 7)),
        ('ALIGN', (0, 7), (3, 7), 'CENTER'),
        ('FONT', (0, 11), (-1, 11), 'Helvetica'),


        # Advance row → SAME as QR code Difference
        ('FONT', (0, 12), (-1, 12), 'Helvetica'),   # 🔧 removed SPAN
        ('ALIGN', (3, 12), (3, 12), 'RIGHT'),

        ('FONT', (0, 8), (-1, 8), 'Helvetica-Bold'),
        ('SPAN', (0, 8), (2, 8)),
        ('ALIGN', (0, 8), (2, 8), 'CENTER'),

        ('FONT', (0, 13), (-1, 13), 'Helvetica-Bold'),
        ('SPAN', (0, 13), (2, 13)),  
        ('ALIGN', (0, 13), (2, 13), 'CENTER'),

        ('FONT', (0, 14), (-1, 14), 'Helvetica-Bold'),
        ('SPAN', (0, 14), (2, 14)),
        ('ALIGN', (0, 14), (2, 14), 'CENTER'),
        ('ALIGN', (3, 14), (3, 14), 'RIGHT'),

        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (1, 1), (1, -2), 'CENTER'),
        ('ALIGN', (2, 1), (3, -3), 'RIGHT'),

        ('FONT', (0, 15), (2, 15), 'Helvetica-Bold'),
        ('ALIGN', (0, 15), (2, 15), 'CENTER'),
        ('SPAN', (1, 15), (3, 15)),

        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 2)
    ]))

    earnings_table.wrapOn(c, width, height)
    earnings_table.drawOn(c, 50, y)

    # Move below table
    y -= (len(earnings_data) * 18 + 10)  # smaller offset

    # Ensure y is not too low
    if y < 50:
        y = 50

    # y -= 30
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, y, "***This is a system-generated salary slip***")

    c.save()
    return pdf_path

# ---------------------------
# 📝 Generate Payslips
# ---------------------------
@app.route("/generate-pdf", methods=["POST"])
def generate_all_pdfs():
    global last_uploaded_file

    if not last_uploaded_file or not os.path.exists(last_uploaded_file):
        return jsonify({"error": "No uploaded file found"}), 400

    import glob

    # Clean up old PDFs before generating new ones
    for file in glob.glob(os.path.join(PDF_FOLDER, "*.pdf")):
        os.remove(file)

    # Read Excel
    df = pd.read_excel(last_uploaded_file, header=1)
    df.columns = [str(col).strip().lower().replace("\n", " ").replace("\r", " ")
                  for col in df.columns]

    generated_files = []

    for index, row in df.iterrows():
        try:
            filename = f"Payslip_{row['valuator id']}.pdf"
            pdf_path = generate_payslip(row.to_dict(), filename)

            raw_email = row.get("email", "")
            email = str(raw_email).strip() if pd.notna(raw_email) and str(raw_email).strip().lower() != "nan" else None
            name = str(row.get("valuator name", "")).strip()

            if email:
                send_email_with_attachment(email, name, pdf_path)
            else:
                print(f"Skipping email for {name} — invalid or missing email.")

            generated_files.append(pdf_path)

        except KeyError as e:
            print(f"Skipping row {index} due to missing column: {e}")

    if not generated_files:
        return jsonify({"error": "No payslips generated. Check column names and data."}), 400

    return jsonify({
        "message": "PDFs generated successfully",
        "files": generated_files
    }), 200

@app.route("/view-payslip/<string:valuator_id>", methods=["GET"])
def view_payslip(valuator_id):
    """Always regenerate and serve latest payslip for a valuator ID"""
    try:
        global last_uploaded_file

        if not last_uploaded_file or not os.path.exists(last_uploaded_file):
            return jsonify({"error": "No uploaded Excel file available"}), 400

        # Load Excel
        df = pd.read_excel(last_uploaded_file, header=1)
        df.columns = [str(col).strip().lower() for col in df.columns]

        # Find matching row
        row = df[df["valuator id"].astype(str).str.upper() == valuator_id.upper()]
        if row.empty:
            return jsonify({"error": f"No data found for ID {valuator_id}"}), 404

        data = row.iloc[0].to_dict()
        filename = f"Payslip_{valuator_id}.pdf"
        file_path = os.path.join(PDF_FOLDER, filename)

        print("### Regenerating payslip for:", valuator_id)

        # Always regenerate the PDF
        generate_payslip(data, filename)

        # Send freshly generated file
        response = make_response(send_file(file_path, mimetype="application/pdf"))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/send-all-mails", methods=["POST"])
def send_all_mails():
    try:
        if not os.listdir(UPLOAD_FOLDER):
            return jsonify({"error": "No uploaded files found"}), 400

        # ✅ Step 1: Clear old PDFs
        for old_file in os.listdir(PDF_FOLDER):
            if old_file.endswith(".pdf"):
                os.remove(os.path.join(PDF_FOLDER, old_file))

        # ✅ Step 2: Read latest uploaded Excel
        file_path = os.path.join(UPLOAD_FOLDER, os.listdir(UPLOAD_FOLDER)[0])
        df = pd.read_excel(file_path, header=1)
        df.columns = [
            str(col).strip().lower().replace("\n", " ").replace("\r", " ")
            for col in df.columns
        ]

        sent_count = 0

        # ✅ Step 3: Generate fresh PDF and send email
        for _, row in df.iterrows():
            valuator_id = str(row["valuator id"]).strip()
            email = str(row.get("email", "")).strip()
            name = str(row.get("valuator name", "")).strip()
            cc_email = str(row.get("cc_email", "")).strip() if "cc_email" in df.columns else None

            # Regenerate payslip fresh
            pdf_file = generate_payslip(row.to_dict(), f"Payslip_{valuator_id}.pdf")

            if email and os.path.exists(pdf_file):
                send_email_with_attachment(email, name, pdf_file,cc_email)
                sent_count += 1
            else:
                print(f"Skipping {valuator_id} - No email or PDF not found")

        return jsonify({"message": f"Emails sent to {sent_count} recipients"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 👉 Download All PDFs as ZIP
@app.route("/download-all")
def download_all():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    PDF_FOLDER = os.path.join(BASE_DIR, "pdfs")
    ZIP_PATH = os.path.join(PDF_FOLDER, "all_payslips.zip")

    # Always delete old ZIP if it exists
    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)

    # ✅ Create zip with only PDF files
    with zipfile.ZipFile(ZIP_PATH, 'w') as zipf:
        for filename in os.listdir(PDF_FOLDER):
            if filename.endswith('.pdf'):
                full_path = os.path.join(PDF_FOLDER, filename)
                zipf.write(full_path, arcname=filename)

    # ✅ Send from correct path
    return send_file(ZIP_PATH, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)