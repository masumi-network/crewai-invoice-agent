"""
Utility functions for exporting data to different formats.
"""
import json
import pandas as pd
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
from fpdf import FPDF
import os
import tempfile
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import random
from datetime import datetime


logger = logging.getLogger(__name__)

def export_invoice_to_pdf(invoice_data: Dict, filename: Optional[str] = None) -> str:
    """
    Export structured invoice data to a PDF file.
    
    Args:
        invoice_data: Structured invoice data with fields for sender, recipient, due date, and transactions
        filename: Output filename (optional)
        
    Returns:
        Path to the exported file
    """
    timestamp = datetime.now().strftime("%Y%M%S")
   
    
    current_date =  datetime.now().strftime("%d %B, %Y")
    if filename is None:
        filename = f"invoice_{timestamp}.pdf"
    
    print("EXPORT DATA",invoice_data)
    pdf = FPDF()
    pdf.add_page()
    
    # Set up fonts
    pdf.set_font("Arial", "", 12)
    pdf.set_fill_color(r =24, g =244, b = 84)
    pdf.cell(0, 5, "", ln=True, fill = True)
    pdf.set_fill_color(r =255)
    pdf.set_font("Arial", "", 15)
    pdf.cell(0, 20, "", ln=True, fill = True)


    pdf.set_font("Helvetica", "B", 25)
    pdf.cell(20, 10, "INVOICE", ln=True, align="L")

    #pdf.set_font("Arial", "", 12)
    #pdf.cell(0, 10, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
    #pdf.ln(10)
    
    # Sender and Recipient Information
    
    pdf.cell(0, 20, "", ln=True, fill = True)
    if invoice_data['logo'] and invoice_data['logo'] != 'None':
        pdf.image(invoice_data['logo'],x = 155, y= 20 ,w = 35, h = 35)


    invoice_number = str(timestamp)
    issue_date = current_date
    due_date = invoice_data['due_date']
    start_y = pdf.get_y()


    pdf.set_font("Helvetica", "", 12)
    pdf.cell(125)
    pdf.cell(40, 0, "Invoice Number", ln=True, align="L")
    pdf.ln(5)
    pdf.cell(125)
    pdf.cell(40, 0, "Issue Date", ln=True, align="L")
    pdf.ln(5)
    pdf.cell(125)
    pdf.cell(40, 0, "Due Date", ln=True, align="L")

    pdf.set_y(start_y)  # Move to right column
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(165)
    pdf.cell(0, 0, invoice_number, ln=True, align="L")
    pdf.ln(5)
    pdf.cell(165)
    pdf.cell(0, 0, issue_date, ln=True, align="L")
    pdf.ln(5)
    pdf.cell(165)
    pdf.cell(0, 0, due_date, ln=True, align="L")

    pdf.set_xy(10, start_y) 
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 0, invoice_data['sender_info'][0], ln=True, align="L")
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 12)
    for line in invoice_data['sender_info'][1:]:
        pdf.cell(0, 0, line, ln=True, align="L")
        pdf.ln(5)

    pdf.cell(0, 0, invoice_data['sender_country'], ln=True, align="L")
    pdf.ln(5)
    if invoice_data['sender_VAT'] and invoice_data['sender_VAT'] != 'None':
        pdf.cell(0, 0, invoice_data['sender_VAT'], ln=True, align="L")
        pdf.ln(5)
    

    """""
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Recipient Information", ln=True)
    pdf.set_font("Arial", "", 12)
    recipient_info = invoice_data['recipient_info']
    pdf.multi_cell(0, 8, recipient_info)
    pdf.ln(5)
    """""
 
    # Due Date
   
    
    # Transactions
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Bill To", ln=True)
    current_x, current_y = pdf.get_x(), pdf.get_y()
    pdf.line(current_x,current_y,current_x+50,current_y)
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 0, invoice_data['recipient_info'][0], ln=True, align="L")
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 12)
    for line in invoice_data['recipient_info'][1:]:
        pdf.cell(0, 0, line, ln=True, align="L")
        pdf.ln(5)

    pdf.cell(0, 0, invoice_data['recipient_country'], ln=True, align="L")
    pdf.ln(5)
    if invoice_data['reciever_VAT'] and invoice_data['reciever_VAT'] != 'None':
        pdf.cell(0, 0, invoice_data['reciever_VAT'], ln=True, align="L")
       
    pdf.ln(15)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(80, 10, "Description", 1)
    pdf.cell(30, 10, "Quantity", 1)
    pdf.cell(40, 10, "Unit Price", 1)
    pdf.cell(40, 10, "Unit Total", 1)
    pdf.ln()

    # Transaction Data
    pdf.set_font("Helvetica", "", 12)
    subtotal = 0
    for i in range(len(invoice_data['transactions'])):
        description = invoice_data['transactions'][i]
        quantity = invoice_data['quantities'][i]
        unit_price = invoice_data['unit_prices'][i]
        unit_total = invoice_data['unit_totals'][i]

        pdf.cell(80, 10, description, 1)
        pdf.cell(30, 10, str(quantity), 1)
        pdf.cell(40, 10, unit_price, 1)
        pdf.cell(40, 10, unit_total, 1)
        pdf.ln()

          # Accumulate subtotal

    # Subtotal
    pdf.set_font("Helvetica", "B", 12)# No border
    pdf.cell(30, 10, "", 0)  # Empty cell for spacing
    pdf.cell(80, 10, "", 0)
    pdf.cell(40, 10, "Subtotal", 0)
    pdf.cell(40, 10, invoice_data['total'], 0)  # Subtotal value
    pdf.ln()

    total = subtotal
    pdf.cell(30, 10, "", 0)
    pdf.cell(80, 10, "", 0)
    pdf.cell(40, 10, "Total", 0)
    pdf.cell(40, 10, invoice_data['total'], 0)
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 12)  # Set font for payment notes
    pdf.cell(0, 10, "Payment Notes:", ln=True, align="L")  # Label for payment notes
    pdf.multi_cell(0, 10, invoice_data['payment_notes'], align="L")  # Payment notes field

    pdf.output(filename)
    return filename