"""
CrewAI agents for Invoice generation
"""
from crewai import Agent, Task, Crew, Process
from typing import Dict, List, Any, Optional
import pandas as pd
import logging
import os
import traceback
import openai
import json
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

class Agents:
    """
    Invoice creator agents using CrewAI.
    """
    
    def __init__(self, invoice_text: str, openai_api_key: Optional[str] = None):
        """
        Initialize the invoice processing agents.
        
        Args:
            invoice_text: String containing the invoice information
            openai_api_key: OpenAI API key for CrewAI agents
        """
        self.invoice_text = invoice_text
        self.openai_api_key = openai_api_key
        self.openai_api_key = openai_api_key
        
        # Set OpenAI API key as environment variable if provided
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key
            # Also set it directly in the openai module
            openai.api_key = openai_api_key
            
            # Log that we've set the API key
            logger.info("OpenAI API key has been set")
            
            # Test the OpenAI API key
            try:
                # Simple test call to OpenAI
                llm = ChatOpenAI(
                    model_name="gpt-3.5-turbo",
                    temperature=0.7,
                    openai_api_key=openai_api_key
                )
                response = llm.invoke("Test")
                logger.info("OpenAI API key is valid")
            except Exception as e:
                logger.error(f"Error testing OpenAI API key: {str(e)}")
                logger.error(traceback.format_exc())
                raise ValueError(f"Invalid OpenAI API key: {str(e)}")
    
    def create_agents(self):
        """
        Create the financial analysis agents.
        
        Returns:
            Tuple of (data_analyst, financial_advisor, budget_optimizer) agents
        """
        # Create a language model
        llm = ChatOpenAI(
            model_name="gpt-4",
            temperature=0.7
        )
        
        # Data Analyst Agent
        invoice_parser  = Agent(
            role="Invoice Parser",
            goal="Parse input text to extract invoice information",
            backstory="""You are an expert in parsing and understanding invoice data. 
            You can accurately identify and extract key information from unstructured text.""",
            verbose=True,
            allow_delegation=False,
            llm=llm
        )
        
        # Field seperator agent
        field_separator = Agent(
            role="Field Separator",
            goal="Separate parsed invoice information into structured fields",
            backstory="""You specialize in organizing parsed data into structured formats. 
            You ensure that all relevant invoice details are correctly categorized.""",
            verbose=True,
            allow_delegation=False,
            llm=llm
        )
        
        return invoice_parser, field_separator

    
    def create_tasks(self, invoice_parser,field_separator):
        """
        Create tasks for the financial analysis agents.
        
        Args:
            invoice_parser: The invoice parser agent
            field_separator: The field separator agent
         
        Returns:
            List of tasks
        """
        # Example input text for an invoice
        invoice_text = self.invoice_text
        
        # Parse the data for the invoice creator
        parsing_task = Task(
            description=f"""
            Parse the following invoice text to extract key information:
            
            {invoice_text}
            
            Focus on identifying:
            1. Sender information
            2. Recipient information
            3. Due date
            4. Transactions
            
            Your output should be a structured representation of the invoice data.
            """,
            agent=invoice_parser,
            expected_output="Structured invoice data with fields for sender, recipient, due date, and transactions."
        )
        
        # Create a financial advice task
        separation_task = Task(
            description=f"""
            Organize the parsed invoice information into structured fields:
            
            - Sender Info
            - Recipient Info
            - Due Date
            - Transactions
            
            Ensure that each field is clearly defined and contains the correct information.
            """,
            agent=field_separator,
            expected_output="Separated fields with clear definitions for each invoice component."
        )
        
        return [parsing_task, separation_task]

        
    
    def run_analysis(self):
        """
        Run the invoice parsing and field separation using CrewAI.
        
        Returns:
            Dictionary with the parsed and structured invoice data
        """
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is required for AI analysis")
        
        try:
            logger.info("Starting invoice processing")
            
            # Check if OpenAI API key is set
            if not os.environ.get("OPENAI_API_KEY"):
                logger.error("OpenAI API key is not set")
                return {
                    "error": "OpenAI API key is not set. Please provide a valid OpenAI API key."
                }
            
            # Create agents
            invoice_parser, field_separator = self.create_agents()
            
            # Create tasks
            tasks = self.create_tasks(invoice_parser, field_separator)
            
            # Create a crew with the agents and tasks
            crew = Crew(
                agents=[invoice_parser, field_separator],
                tasks=tasks,
                verbose=True,
                process=Process.sequential
            )
            
            # Run the crew
            logger.info("Running CrewAI invoice processing")
            result = crew.kickoff()
            logger.info("Invoice processing complete")
            
            # Process results
            logger.info("Processing results...")
            
            try:
                # Extract results from the crew's output
                parsed_invoice = ""
                structured_fields = ""
                
                # Log the type and structure of the result for debugging
                logger.info(f"Result type: {type(result)}")
                logger.info(f"Result attributes: {dir(result)}")
                
                # Check if the result has tasks attribute (newer CrewAI versions)
                if hasattr(result, 'tasks'):
                    logger.info(f"Found tasks attribute with {len(result.tasks)} tasks")
                    for i, task_result in enumerate(result.tasks):
                        logger.info(f"Processing task {i+1}")
                        task_description = task_result.description.lower() if hasattr(task_result, 'description') else ""
                        task_output = task_result.output if hasattr(task_result, 'output') else ""
                        
                        if "parse the following invoice text" in task_description:
                            parsed_invoice = task_output
                        elif "organize the parsed invoice information" in task_description:
                            structured_fields = task_output
                
                # If we still don't have results, use the string representation of the result
                if not parsed_invoice:
                    logger.info("Using string representation of result")
                    result_str = str(result)
                    
					 # Try to extract sections based on headers
                    if "# Parsed Invoice" in result_str:
                        parts = result_str.split("# Parsed Invoice")
                        if len(parts) > 1:
                            parsed_invoice = parts[1].strip()
                            if "# Structured Fields" in parsed_invoice:
                                parsed_invoice, structured_fields = parsed_invoice.split("# Structured Fields")
                                structured_fields = structured_fields.strip()
                
                return {
                    "parsed_invoice": parsed_invoice,
                    "structured_fields": structured_fields
                }
            
            except Exception as e:
                logger.error(f"Error processing results: {e}", exc_info=True)
                error_message = f"Error processing results: {str(e)}\n\n"
                error_message += traceback.format_exc()
                
                return {
                    "error": error_message
                }
        except Exception as e:
            logger.error(f"Error in run_analysis: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Return a meaningful error message
            return {
                "error": f"Error during analysis: {str(e)}"
            }
					