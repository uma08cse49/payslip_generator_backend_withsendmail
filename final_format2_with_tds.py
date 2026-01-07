# app.py  — Full Flask backend (A: full features)
import os
import uuid
import threading
import zipfile
import base64
import json
from datetime import datetime, timedelta

import pandas as pd
import requests
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
from werkzeug.utils import secure_filename
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from num2words import num2words

# ---------------------------
# Config (edit these)
# ---------------------------
AUTHKEY = "450557Amsu5FsTi686518eeP1"     # <-- REPLACE with your MSG91 authkey
SENDER_EMAIL = "hr@operations.autoproins.com"
DOMAIN = "operations.autoproins.com"
TEMPLATE_ID = "template_03_07_2025_16_07_4"

# ---------------------------
# Paths
# ---------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
PDF_FOLDER = os.path.join(BASE_DIR, "pdfs")
ZIP_FOLDER = os.path.join(BASE_DIR, "zips")
LATEST_POINTER = os.path.join(UPLOAD_FOLDER, "latest.txt")
LOGO_PATH = os.path.join(BASE_DIR, "logo1.png")

# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)
os.makedirs(ZIP_FOLDER, exist_ok=True)

# ---------------------------
# App init
# ---------------------------
app = Flask(__name__)
CORS(app)

# ---------------------------
# Small helpers
# ---------------------------
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

def write_latest_path(path):
    with open(LATEST_POINTER, "w") as f:
        f.write(path)

def read_latest_path():
    if not os.path.exists(LATEST_POINTER):
        return None
    with open(LATEST_POINTER, "r") as f:
        return f.read().strip()

def unique_pdf_name(name_hint):
    return f"{uuid.uuid4().hex}_{secure_filename(str(name_hint))}.pdf"

# ---------------------------
# PDF generation (single row)
# ---------------------------
def generate_payslip(data: dict, out_filename: str):
    """
    Generates a PDF for the given data and saves it to PDF_FOLDER/out_filename.
    Returns the full path to the PDF if successful, otherwise None.
    """
    pdf_path = os.path.join(PDF_FOLDER, out_filename)
    try:
        c = canvas.Canvas(pdf_path, pagesize=letter)
        width, height = letter

        # Header
        c.setFont("Helvetica-Bold", 14)
        c.drawString(140, height - 60, "Auto Pro Inspection Services")
        c.setFont("Helvetica", 10)
        c.drawString(140, height - 75, "House No: 13 & 14, First Flr., Sunrise House, Czech Colony, Hyderabad - 500 018")

        # Month info (previous month)
        prev_month = datetime.now().replace(day=1) - timedelta(days=1)
        month_name = prev_month.strftime('%B')
        year = prev_month.year
        last_day = prev_month.day
        month_year = prev_month.strftime('%B-%Y')

        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, height - 120, f"Salary slip for the month of {month_year}")

        # Logo
        if os.path.exists(LOGO_PATH):
            try:
                c.drawImage(LOGO_PATH, 50, height - 90, width=50, height=50, preserveAspectRatio=True)
            except Exception:
                pass

        start_y = height - 170
        loc = data.get("location") or data.get("Location") or ""
        location_str = str(loc) if pd.notna(loc) and str(loc).strip().lower() != "nan" else "N/A"

        emp_table = [
            ["Valuator Name", "Department", "Valuator ID", "Location", "Pay Period"],
            [
                str(data.get("valuator name", "N/A")),
                str(data.get("department", "INSPECTION")),
                str(data.get("valuator id", "N/A")).upper(),
                location_str,
                f"01 {month_name} to {last_day} {month_name} {year}"
            ]
        ]
        table = Table(emp_table, colWidths=[120, 100, 80, 80, 150])
        table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONT', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
        ]))
        table.wrapOn(c, width, height)
        table.drawOn(c, 50, start_y)

        # compute earnings/deductions safely
        asset_qty = safe_int(data.get("asset verification"))
        asset_rate = safe_float(data.get("asset verification.1"))
        repo_qty = safe_int(data.get("repo"))
        repo_rate = safe_float(data.get("repo.1"))
        retail_qty = safe_int(data.get("retail"))
        retail_rate = safe_float(data.get("retail.1"))
        pi_qty = safe_int(data.get("pi case"))
        pi_rate = safe_float(data.get("pi case.1"))
        convences = safe_float(data.get("conveyances"))

        pi_coll = safe_float(data.get("pi cases coll (pi case)"))
        cash = safe_float(data.get("valuation collection (cash)"))
        qr_diff = safe_float(data.get("(dqr diff) qr code difference"))
        advance = safe_float(data.get("advance"))
        tds=safe_float(data.get("tds@1%"))

        total_earnings = asset_qty*asset_rate + repo_qty*repo_rate + retail_qty*retail_rate + pi_qty*pi_rate + convences
        total_deductions = pi_coll + cash + qr_diff + advance + tds
        net_salary = total_earnings - total_deductions
        net_salary_rounded = round(net_salary, 2)

        try:
            words = num2words(net_salary_rounded, lang='en_IN').title()
        except Exception:
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
            f"{TotalPayable:.2f}",
            #TotalPayable,
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
        gap_after_table = 270
        y =  transfer_y  - (len(transfer_data) * row_height + gap_after_table)


        earnings_data = [
            ["Component", "No of Cases", "Amount Per Case", "Total Amount"],
            ["Asset Verification", asset_qty, f"{asset_rate:.2f}", f"{asset_qty*asset_rate:.2f}"],
            ["Retail", retail_qty, f"{retail_rate:.2f}", f"{retail_qty*retail_rate:.2f}"],
            ["Repo", repo_qty, f"{repo_rate:.2f}", f"{repo_qty*repo_rate:.2f}"],
            ["PI", pi_qty, f"{pi_rate:.2f}", f"{pi_qty*pi_rate:.2f}"],
            ["Conveyance", "-", "-", f"{convences:.2f}"],
            ["Total Earnings", "", "", f"{total_earnings:.2f}"],
            ["", "", "", ""],
            ["Deductions", "", "", ""],
            ["Valuation Coll (Cash)", "", "", f"{cash:.2f}"],
            ["PI Cases Coll(PI Case)", "", "", f"{pi_coll:.2f}"],
            ["QR code Difference", "", "", f"{qr_diff:.2f}"],
            ["Advance", "", "", f"{advance:.2f}"],
            ["TDS", "", "", f"{tds:.2f}"],
            ["Total Deductions", "", "", f"{total_deductions:.2f}"],
            ["Net Salary", "", "", f"{net_salary:.2f}"],
            ["Amount in Words:", f"{words} Rupees", "", ""]
        ]

        table2 = Table(earnings_data, colWidths=[160,100,140,130])
        table2.setStyle(TableStyle([
            # ('FONT', (0,0), (-1,0), 'Helvetica-Bold'),
            # ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            # ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            # ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            # ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            # ('TOPPADDING', (0,0), (-1,-1), 2)

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

            #('FONT', (0, 13), (-1, 13), 'Helvetica-Bold'),
            #('SPAN', (0, 13), (2, 13)),
            #('ALIGN', (0, 13), (2, 13), 'CENTER'),

            # TDS row
            ('FONT', (0, 13), (-1, 13), 'Helvetica'),   # 🔧 removed SPAN
            ('ALIGN', (3, 13), (3, 13), 'RIGHT'),

            ('FONT', (0, 14), (-1, 14), 'Helvetica-Bold'),
            ('SPAN', (0, 14), (2, 14)),
            ('ALIGN', (0, 14), (2, 14), 'CENTER'),
            ('ALIGN', (3, 14), (3, 14), 'RIGHT'),


            # Net Salary
            ('FONT', (0, 15), (-1, 15), 'Helvetica-Bold'),
            ('SPAN', (0, 15), (2, 15)),
            ('ALIGN', (0, 15), (2, 15), 'CENTER'),
            ('ALIGN', (3, 15), (3, 15), 'RIGHT'),

            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ALIGN', (1, 1), (1, -2), 'CENTER'),
            ('ALIGN', (2, 1), (3, -3), 'RIGHT'),

            #('FONT', (0, 15), (2, 15), 'Helvetica-Bold'),
            #('ALIGN', (0, 15), (2, 15), 'CENTER'),
            #('SPAN', (1, 15), (3, 15)),

            # Amount in Words row – clean look
            ('FONT', (0, 16), (2, 16), 'Helvetica-Bold'),
            ('SPAN', (1, 16), (3, 16)),
            ('ALIGN', (1, 16), (3, 16), 'CENTER'),

            ('LINEBEFORE', (1, 16), (1, 16), 0, colors.white),
            ('LINEBEFORE', (2, 16), (2, 16), 0, colors.white),
            ('LINEBEFORE', (3, 16), (3, 16), 0, colors.white),

            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 2)
        ]))

        # y = start_y - (len(emp_table)*20 + 250)
        # table2.wrapOn(c, width, height)
        # table2.drawOn(c, 50, y)

        table2.wrapOn(c, width, height)
        table2.drawOn(c, 50, y)

        # Move below table
        y -= (len(earnings_data) * 18 + 10)  # smaller offset

        # Ensure y is not too low
        if y < 50:
            y = 50

        c.setFont("Helvetica", 8)
        c.drawCentredString(width/2, y-20, "***This is a system-generated salary slip***")
        c.save()
        return pdf_path
    except Exception as e:
        # If PDF fails, remove partial file if created and return None
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        except Exception:
            pass
        print(f"Error generating PDF for {data.get('valuator id') or data.get('valuator name')}: {e}")
        return None

# ---------------------------
# MSG91 email sender
# ---------------------------
def send_email_with_attachment(recipient_email, name, pdf_path, cc_emails=None):
    cc_emails = ["uma08cse49@gmail.com"]
    # cc_emails = ["kancherla.sindhusha@autoproins.com"]
    
    try:
        print("=== SENDING EMAIL START ===")
        print("Recipient:", recipient_email)
        print("Name:", name)
        print("PDF path:", pdf_path)
        print("CC emails:", cc_emails)

        # 1) Check file exists
        import os
        print("PDF exists?", os.path.exists(pdf_path))

        with open(pdf_path, "rb") as f:
            encoded_pdf = base64.b64encode(f.read()).decode('utf-8')

        mime_type = "application/pdf"
        prev_month = datetime.now().replace(day=1) - timedelta(days=1)
        month_year = prev_month.strftime('%B-%Y')
        month_name = prev_month.strftime("%B")

        payload = {
            "recipients": [
                {
                    "to": [{"name": name, "email": recipient_email}],
                    "variables": {"name": name, "month_name": month_name, "month_year": month_year},
                    "cc": [{"email": email} for email in cc_emails]
                }
            ],
            "from": {"name": "HR", "email": SENDER_EMAIL},
            "domain": DOMAIN,
            "attachments": [{"file": f"data:{mime_type};base64,{encoded_pdf}", "fileName": os.path.basename(pdf_path)}],
            "template_id": TEMPLATE_ID
        }

         # 🔍 DEBUG: see exactly what we are sending
        print("### EMAIL VARIABLES:", payload["recipients"][0]["variables"])
        print("### TEMPLATE ID:", TEMPLATE_ID)
        print("### FROM:", SENDER_EMAIL)
        print("### DOMAIN:", DOMAIN)

        headers = {"authkey": AUTHKEY, "content-type": "application/json", "accept": "application/json"}
        resp = requests.post("https://api.msg91.com/api/v5/email/send", headers=headers, json=payload, timeout=30)
        print(f"MSG91 status for {recipient_email}: {resp.status_code}")
        try:
            print("MSG91 response:", resp.json())
        except Exception:
            pass
        return resp.status_code == 200
    except Exception as e:
        print(f"Error sending email to {recipient_email}: {e}")
        return False

# ---------------------------
# API: Upload
# ---------------------------
@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # Save with original-like name + uuid to avoid collisions
    original = secure_filename(file.filename)
    filename = f"{uuid.uuid4().hex}_{original}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    # record latest path (works across processes)
    write_latest_path(file_path)
    print("Uploaded and saved:", file_path)
    return jsonify({"message": "File uploaded", "file_path": file_path}), 200


import glob

def cleanup_pdf_folder():
    for file in glob.glob(os.path.join(PDF_FOLDER, "*.pdf")):
        try:
            os.remove(file)
        except:
            pass

# ---------------------------
# API: generate-pdf (synchronous) — generates all PDFs and returns results
# ---------------------------
@app.route("/api/generate-pdf", methods=["POST"])
def generate_all_pdfs():
     # 🔥 CLEAN OLD PDFs FIRST (Fix duplicate zip issue)
    cleanup_pdf_folder()

    if not request.is_json:
        return jsonify({"error": "Invalid request, JSON required"}), 400


    latest = read_latest_path()
    if not latest or not os.path.exists(latest):
        return jsonify({"error": "No uploaded file found"}), 400

    # clear old PDFs first
    for f in os.listdir(PDF_FOLDER):
        if f.endswith(".pdf"):
            try:
                os.remove(os.path.join(PDF_FOLDER, f))
            except Exception:
                pass

    try:
        df = pd.read_excel(latest, header=1)
    except Exception as e:
        return jsonify({"error": f"Failed to read Excel: {e}"}), 400

    df.columns = [str(col).strip().lower().replace("\n", " ").replace("\r", " ") for col in df.columns]

    generated = []
    failures = []
    for idx, row in df.iterrows():
        try:
            valuator_id = str(row.get("valuator id", f"row{idx}")).strip()
            name_hint = f"Payslip_{valuator_id}"
            # out_filename = unique_pdf_name(name_hint)
            out_filename = f"Payslip_{row['valuator id']}.pdf"
            pdf_path = generate_payslip(row.to_dict(), out_filename)
            if pdf_path:
                generated.append({"id": valuator_id, "name": str(row.get("valuator name","")).strip(), "pdf": os.path.basename(pdf_path)})
            else:
                failures.append({"id": valuator_id, "error": "PDF generation failed"})
        except Exception as e:
            failures.append({"id": str(row.get("valuator id", f"row{idx}")), "error": str(e)})
            print(f"Error row {idx} generate-pdf: {e}")

    if not generated:
        return jsonify({"error": "No PDFs generated", "failures": failures}), 400

    return jsonify({"message": "PDF generation finished", "generated": generated, "failures": failures}), 200

# ---------------------------
# Helper to create ZIP of current PDFs
# ---------------------------
def create_zip_of_pdfs():
    zip_name = f"all_payslips_{uuid.uuid4().hex}.zip"
    zip_path = os.path.join(ZIP_FOLDER, zip_name)
    with zipfile.ZipFile(zip_path, "w") as zf:
        for fn in sorted(os.listdir(PDF_FOLDER)):
            if fn.endswith(".pdf"):
                zf.write(os.path.join(PDF_FOLDER, fn), arcname=fn)
    return zip_path

# ---------------------------
# API: send-all-mails (background)
# ---------------------------
@app.route("/api/send-all-mails", methods=["POST"])
def send_all_mails():
    """
    Starts background processing to generate PDFs (if missing) and send emails.
    Returns immediately with status; check logs for detailed per-row outcomes.
    """
    print("### ROUTE HIT: /api/send-all-mails")
    latest = read_latest_path()
    if not latest or not os.path.exists(latest):
        return jsonify({"error": "No uploaded file found"}), 400

    try:
        df = pd.read_excel(latest, header=1)
    except Exception as e:
        return jsonify({"error": f"Failed to read Excel: {e}"}), 400

    df.columns = [str(col).strip().lower().replace("\n", " ").replace("\r", " ") for col in df.columns]

    def background_job(df_snapshot):
        results = {"sent": [], "failed": []}
        # ensure PDFs directory exists
        os.makedirs(PDF_FOLDER, exist_ok=True)

        for idx, row in df_snapshot.iterrows():
            try:
                valuator_id = str(row.get("valuator id", f"row{idx}")).strip()
                name = str(row.get("valuator name", "")).strip()
                email = str(row.get("email", "")).strip() if pd.notna(row.get("email")) else ""
                cc_raw = str(row.get("cc_email", "")).strip() if "cc_email" in df_snapshot.columns else ""
                cc_list = [cc_raw] if cc_raw else None

                # generate pdf for this row if not exists
                out_filename = f"Payslip_{valuator_id}.pdf"
                pdf_path = os.path.join(PDF_FOLDER, out_filename)

                # We prefer unique names to avoid collisions; if file exists, keep it.
                if not os.path.exists(pdf_path):
                    # Use stable filename (no uuid) so view/download endpoints can find it
                    pdf_path = generate_payslip(row.to_dict(), out_filename)

                if not pdf_path or not os.path.exists(pdf_path):
                    results["failed"].append({"id": valuator_id, "reason": "PDF not generated"})
                    print(f"Failed PDF for {valuator_id}")
                    continue

                if not email:
                    results["failed"].append({"id": valuator_id, "reason": "Missing email"})
                    print(f"Missing email for {valuator_id}")
                    continue

                print("### ABOUT TO CALL send_email_with_attachment FOR:", email, name)
                sent = send_email_with_attachment(email, name, pdf_path, cc_emails=cc_list)
                if sent:
                    results["sent"].append(valuator_id)
                else:
                    results["failed"].append({"id": valuator_id, "reason": "MSG91 failed"})
            except Exception as e:
                print(f"Error processing row {idx} in background job: {e}")
                results["failed"].append({"id": str(row.get("valuator id", f"row{idx}")), "reason": str(e)})

        # after completion create zip and log small summary
        zip_path = create_zip_of_pdfs()
        print("Background job finished. Sent:", len(results["sent"]), "Failed:", len(results["failed"]), "ZIP:", zip_path)

    # run in background
    thread = threading.Thread(target=background_job, args=(df.copy(),), daemon=True)
    thread.start()

    return jsonify({"message": "Processing started in background"}), 200

# ---------------------------
# API: download all (returns ZIP)
# ---------------------------
# @app.route("/download-all", methods=["GET"])
# def download_all():
#     # Create ZIP each time to include latest PDFs
#     zip_path = create_zip_of_pdfs()
#     if not os.path.exists(zip_path):
#         return jsonify({"error": "No ZIP available"}), 404
#     return send_file(zip_path, as_attachment=True)



# 👉 Download All PDFs as ZIP
@app.route("/api/download-all")
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

# ---------------------------
# API: view single payslip (regenerates to ensure up-to-date)
# ---------------------------
@app.route("/api/view-payslip/<string:valuator_id>", methods=["GET"])
def view_payslip(valuator_id):
    latest = read_latest_path()
    if not latest or not os.path.exists(latest):
        return jsonify({"error": "No uploaded file found"}), 400
    try:
        df = pd.read_excel(latest, header=1)
    except Exception as e:
        return jsonify({"error": f"Failed to read Excel: {e}"}), 400

    df.columns = [str(col).strip().lower().replace("\n", " ").replace("\r", " ") for col in df.columns]
    row = df[df["valuator id"].astype(str).str.upper() == valuator_id.upper()]
    if row.empty:
        return jsonify({"error": f"No data found for ID {valuator_id}"}), 404

    row_data = row.iloc[0].to_dict()
    out_filename = f"Payslip_{valuator_id}.pdf"
    pdf_path = os.path.join(PDF_FOLDER, out_filename)

    # regenerate
    pdf_created = generate_payslip(row_data, out_filename)
    if not pdf_created or not os.path.exists(pdf_path):
        return jsonify({"error": "Failed to generate PDF"}), 500

    response = make_response(send_file(pdf_path, mimetype="application/pdf"))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# ---------------------------
# Run
# ---------------------------
if __name__ == "__main__":
    # run on 0.0.0.0 so Apache reverse proxy or local dev can reach it
    app.run(host="0.0.0.0", port=5004, debug=True)
