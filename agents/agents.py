"""
CrewAI agents for Invoice generation
"""
from crewai import Agent, Task, Crew, Process
from typing import Dict, Optional
import logging
import os
import traceback
import openai
import json
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from tools.export import export_invoice_to_pdf  

logger = logging.getLogger(__name__)
# Define the Pydantic model for the blog
class Invoice(BaseModel):
    logo : str
    sender_info : str
    recipient_info : str
    due_date : str
    transactions : list
    quantities : list
    unit_prices : list
    unit_totals : list
    total : str

class Invoice_Agents:
    """
    Invoice creator agent using CrewAI.
    """
    
    def __init__(self, invoice_text: str):
        """
        Initialize the invoice processing agent.
        
        Args:
            invoice_text: String containing the invoice information
            openai_api_key: OpenAI API key for CrewAI agents
        """
        self.invoice_text = invoice_text        
        # Test the OpenAI API ke
    def create_agent(self):
        """
        Create a single agent for parsing invoice data.
        
        Returns:
            The invoice parser agent.
        """
        llm = ChatOpenAI(
            model_name="gpt-4",
            temperature=0.7
        )
        
        invoice_parser = Agent(
            role="Invoice Parser",
            goal="Parse input text to extract invoice information and return it as a structured dictionary.",
            backstory="""You are an expert in parsing and understanding invoice data. 
            You can accurately identify and extract key information from unstructured text.""",
            verbose=True,
            allow_delegation=False,
            llm=llm
        )
        
        return invoice_parser

    def create_task(self, invoice_parser):
        """
        Create a task for the invoice parser agent.
        
        Args:
            invoice_parser: The invoice parser agent
            
        Returns:
            The parsing task.
        """
        invoice_text = self.invoice_text
        
        # Create a parsing task for the AI to identify and extract invoice information
        parsing_task = Task(
            description=f"""
            Parse the following invoice text to extract key information:
            
            {invoice_text}
            
            Focus on identifying:
            1. Sender information
            2. Recipient information
            3. Due date
            4. Transactions (these must be in singular tense e.g. (products -> product))
            5. quantities
            6. Unit prices (price per individual transaction unit)
            7. totals (the total price of each unique transaction unit)
            8. total (sum total of all transactions)
            9. Company logo (will be a hexadecimal number)

            (Do NOT output currency as words, instead use the appropriate symbols and include them in 
             unit prices, totals and the total)

            (Add capital letters to person names and address names)

            (Add a comma (,) at the end of the recipient and sender names (Person or company)to seperate them from their addresses)

            (Write All dates as [NUMBER] [NAME OF MONTH] [YEAR NUMBER])
            
            Return the output as a structured dictionary with the keys:
            - logo (the provided hexadecimal number, if none are present put "None" in this field instead)
            - sender_info
            - recipient_info
            - due_date
            - transactions
            - quantities
            - unit_prices
            - unit_totals
            - total 
            """,
            agent=invoice_parser,
            expected_output="Structured invoice data dicitonary with fields for sender, recipient, due date, and transactions.",
            output_json=Invoice,
        )
        
        return parsing_task

    def run_analysis(self):
        """
        Run the invoice parsing using CrewAI.
        
        Returns:
            Dictionary with the parsed and structured invoice data
        """
        try:
            logger.info("Starting invoice processing")
            
            if not os.environ.get("OPENAI_API_KEY"):
                logger.error("OpenAI API key is not set")
                return {
                    "error": "OpenAI API key is not set. Please provide a valid OpenAI API key."
                }
            
            # Create the agent
            invoice_parser = self.create_agent()
            
            # Create the task
            task = self.create_task(invoice_parser)
            
            # Create a crew with the agent and task
            crew = Crew(
                agents=[invoice_parser],
                tasks=[task],
                verbose=True,
                process=Process.sequential
            )
            
            # Run the crew
            logger.info("Running CrewAI invoice processing")
            result = crew.kickoff()
            logger.info("Invoice processing complete")
            
            # Log the entire result object for debugging
            logger.info(f"Result object: {result}")
            
            # Process results
            logger.info("Processing results...")

            return result
        
        except Exception as e:
            logger.error(f"Error in run_analysis: {str(e)}")
            logger.error(traceback.format_exc())
            
            return {
                "error": f"Error during analysis: {str(e)}"
            }