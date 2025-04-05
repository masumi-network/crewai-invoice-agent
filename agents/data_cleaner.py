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

class Cleaning_Agents:
    """
    Invoice creator agent using CrewAI.
    """
    
    def __init__(self, data: str):
        """
        Initialize the invoice processing agent.
        
        Args:
            invoice_text: String containing the invoice information
            openai_api_key: OpenAI API key for CrewAI agents
        """
        self.data = data        
        # Test the OpenAI API ke
    def create_agents(self):
        """
        Create a single agent for parsing invoice data.
        
        Returns:
            The invoice parser agent and the legal advisor agent.
        """
        llm = ChatOpenAI(
            model_name="gpt-4",
            temperature=0.7
        )
        
        data_cleaner = Agent(
            role="Data Cleaner",
            goal="""Analyse large amounts of data and filter out specified unnecessary data and
            format said data in an easily human readable manner""",
            backstory="""You are an expert in analysing and cleaning input data. 
            You can accurately identify filter out redundant data while re-formatting input data to be easily readable.""",
            verbose=True,
            allow_delegation=False,
            llm=llm
        )

      
        
        return data_cleaner

    def create_task(self, data_cleaner):
        """
        Create a task for the invoice parser agent.
        
        Args:
            invoice_parser: The invoice parser agent
            
        Returns:
            The parsing task.
        """
        data = self.data
        
        # Create a parsing task for the AI to identify and extract invoice information
        cleaning_task = Task(
            description=f"""
            Analyse the following data and clean it:
            
            {data}
            
            The data consists of information collected by scraping websites. As such, focus on removing redundant data such as
            website metadata, external links, button names and anything unrelated to invoice regulations.

            Then, format it properly into a human readable fashion, try to identify sections of text that come from different websites
            and section them appropriately.
            
            """,
            agent=data_cleaner,
            expected_output="A cleaned string containing only relevant invoice regulations", 
        )
        
        return cleaning_task
    def clean_Data(self):
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
            
            # Extract countries from the invoice data
            
            # Create both agents
            data_cleaner = self.create_agents()
            
            # Create both tasks
            cleaning_task = self.create_task(data_cleaner)
            
            # Create crew with both agents and tasks
            crew = Crew(
                agents=[data_cleaner],
                tasks=[cleaning_task],
                verbose=True,
                process=Process.sequential
            )
            
            # Run the crew and get results directly
            logger.info("Running CrewAI invoice processing")
            result = crew.kickoff()
            
            
            logger.info("Invoice processing complete")
            logger.info(f"Result object: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in clean_Data: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "error": f"Error during cleaning: {str(e)}"
            }