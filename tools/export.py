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

logger = logging.getLogger(__name__)

def  export_invoice_to_pdf(invoice_data: Dict, filename: Optional[str] = None) -> str:
    """
    Export structured invoice data to a PDF file.
    
    Args:
        invoice_data: Structured invoice data with fields for sender, recipient, due date, and transactions
        filename: Output filename (optional)
        
    Returns:
        Path to the exported file
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"invoice_{timestamp}.pdf"
    
    print("EXPORT DATA",invoice_data)
    pdf = FPDF()
    pdf.add_page()
    
    # Set up fonts
    pdf.set_font("Arial", "", 12)
    pdf.set_fill_color(r =24, g =244, b = 84)
    pdf.cell(0, 5, "", ln=True, fill = True)
    pdf.set_fill_color(r =255)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 15, "", ln=True, fill = True)


    pdf.set_font("Helvetica", "B", 25)
    pdf.cell(0, 10, "INVOICE", ln=True, align="L")

    #pdf.set_font("Arial", "", 12)
    #pdf.cell(0, 10, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
    #pdf.ln(10)
    
    # Sender and Recipient Information
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Sender Information", ln=True)
    pdf.set_font("Arial", "", 12)
    sender_info = invoice_data['sender_info']
    pdf.multi_cell(0, 8, sender_info)
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Recipient Information", ln=True)
    pdf.set_font("Arial", "", 12)
    recipient_info = invoice_data['recipient_info']
    pdf.multi_cell(0, 8, recipient_info)
    pdf.ln(5)
 
    # Due Date
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Due Date", ln=True)
    pdf.set_font("Arial", "", 12)
    due_date = invoice_data['due_date']
    pdf.cell(0, 8, f"Due Date: {due_date}", ln=True)
    pdf.ln(5)
    
    # Transactions
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Transactions", ln=True)
    pdf.set_font("Arial", "", 12)
    transactions = invoice_data['transactions']
    for transaction in transactions:
        pdf.multi_cell(0, 8, transaction)
    pdf.ln(5)
    
    pdf.output(filename)
    return filename