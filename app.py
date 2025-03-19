"""
CrewAI Invoice generator Agent PDF
"""
import os
import logging
import traceback
from typing import Dict, Optional
from agents.agents import Agents
from tools.export import export_invoice_to_pdf, parse_invoice_text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    print("📄 Invoice Processor with CrewAI")
    print("This script processes invoice data using AI agents and exports the results to a PDF.\n")

    # Get OpenAI API Key
    openai_api_key = input("Enter your OpenAI API Key: ").strip()
    if not openai_api_key:
        print("OpenAI API key is required.")
        return

    # Set the environment variable for OpenAI API key
    os.environ["OPENAI_API_KEY"] = openai_api_key

    # Get Invoice Data
    print("\nEnter Invoice Data (end with a blank line):")
    invoice_lines = []
    while True:
        line = input()
        if line.strip() == "":
            break
        invoice_lines.append(line)
    invoice_text = "\n".join(invoice_lines)

    if not invoice_text.strip():
        print("Invoice data is required.")
        return
        
    
    try:
        # Create invoice processing agents
        agents = Agents(invoice_text, openai_api_key=openai_api_key)
        
        # Run analysis
        results = agents.run_analysis()
        
        # Check for errors
        if "error" in results:
            print(f"Error processing invoice: {results['error']}")
        else:
            print("Invoice processed successfully!")
            
            # Export to PDF
            export_path = export_invoice_to_pdf(results)
            print(f"Invoice exported to PDF: {export_path}")
    
    except Exception as e:
        error_msg = str(e)
        stack_trace = traceback.format_exc()
        print(f"Error processing invoice: {error_msg}")
        print("Error details:")
        print(stack_trace)
        logger.error(f"Error processing invoice: {e}", exc_info=True)
if __name__ == "__main__":
    main()
    