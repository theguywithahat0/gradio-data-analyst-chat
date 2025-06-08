"""
Chat Handler for GCP Data Analyst Agent

Handles communication with the Vertex AI Reasoning Engine agent.
"""

import os
import json
import asyncio
from typing import Dict, Any, Optional
from google.cloud import aiplatform
from google.auth import default
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatHandler:
    """Handles communication with the Vertex AI Reasoning Engine agent"""
    
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_CLOUD_LOCATION", "europe-west1")
        self.agent_name = os.getenv("AGENT_NAME")
        self.agent_full_name = None
        
        # Initialize the client
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Vertex AI client"""
        try:
            # Set up authentication
            credentials, project = default()
            
            if not self.project_id:
                self.project_id = project
            
            # Initialize Vertex AI
            aiplatform.init(
                project=self.project_id,
                location=self.location,
                credentials=credentials
            )
            
            # Initialize the Reasoning Engine client
            self.client = aiplatform.ReasoningEngineServiceClient(
                credentials=credentials
            )
            
            # Build the full agent name if provided
            if self.agent_name:
                self.agent_full_name = f"projects/{self.project_id}/locations/{self.location}/reasoningEngines/{self.agent_name}"
            
            logger.info(f"Initialized ChatHandler for project {self.project_id} in {self.location}")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChatHandler: {e}")
            raise
    
    def send_message(
        self, 
        message: str, 
        user_id: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a message to the agent and return the response
        
        Args:
            message: User's message
            user_id: User identifier
            session_id: Session identifier
            context: Additional context for the agent
            
        Returns:
            Dict containing response and metadata
        """
        try:
            if not self.agent_full_name:
                # If no specific agent is configured, return a mock response
                return self._mock_response(message, user_id)
            
            # Prepare the input for the agent
            agent_input = {
                "message": message,
                "user_id": user_id,
                "session_id": session_id,
                "context": context or {}
            }
            
            # Call the reasoning engine
            request = aiplatform.QueryReasoningEngineRequest(
                name=self.agent_full_name,
                input=agent_input
            )
            
            response = self.client.query_reasoning_engine(request=request)
            
            # Process the response
            result = self._process_response(response, message, user_id)
            
            logger.info(f"Successfully processed message for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error sending message to agent: {e}")
            return {
                "response": f"❌ I'm having trouble processing your request right now. Error: {str(e)}",
                "metadata": {
                    "error": True,
                    "error_message": str(e),
                    "user_id": user_id,
                    "session_id": session_id
                }
            }
    
    def _process_response(
        self, 
        response: Any, 
        original_message: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """Process the agent response and extract relevant information"""
        try:
            # Extract the response content
            if hasattr(response, 'output'):
                agent_output = response.output
            else:
                agent_output = str(response)
            
            # Try to parse as JSON if possible
            try:
                if isinstance(agent_output, str):
                    parsed_output = json.loads(agent_output)
                else:
                    parsed_output = agent_output
                
                # Extract the main response text
                if isinstance(parsed_output, dict):
                    response_text = parsed_output.get("response", str(parsed_output))
                    metadata = parsed_output.get("metadata", {})
                else:
                    response_text = str(parsed_output)
                    metadata = {}
                    
            except json.JSONDecodeError:
                # If not JSON, treat as plain text
                response_text = str(agent_output)
                metadata = {}
            
            # Add processing metadata
            metadata.update({
                "timestamp": aiplatform.utils.get_timestamp(),
                "user_id": user_id,
                "original_message": original_message,
                "processed": True
            })
            
            return {
                "response": response_text,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Error processing agent response: {e}")
            return {
                "response": f"✅ I received your message, but had trouble formatting the response: {str(e)}",
                "metadata": {
                    "error": True,
                    "processing_error": str(e),
                    "user_id": user_id
                }
            }
    
    def _mock_response(self, message: str, user_id: str) -> Dict[str, Any]:
        """Generate a mock response when no agent is configured"""
        
        # Simple mock responses based on message content
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["sql", "query", "select", "database"]):
            response = """🔍 **SQL Query Analysis**

Based on your request, here's what I would typically do:

```sql
SELECT column1, column2, COUNT(*) as count
FROM your_table 
WHERE condition = 'value'
GROUP BY column1, column2
ORDER BY count DESC
LIMIT 10;
```

**Note**: This is a demo response. To get real SQL queries and analysis, please configure the Vertex AI agent connection."""

        elif any(word in message_lower for word in ["chart", "graph", "plot", "visualiz"]):
            response = """📊 **Data Visualization**

I can help you create various types of visualizations:

- **Bar Charts** for categorical comparisons
- **Line Charts** for time series data  
- **Scatter Plots** for correlation analysis
- **Heatmaps** for pattern recognition

**Note**: This is a demo response. Connect the real agent to generate actual visualizations from your data."""

        elif any(word in message_lower for word in ["upload", "file", "data"]):
            response = """📁 **File Analysis**

I can analyze various data formats:

- CSV files with automatic column detection
- Excel files with multiple sheet support
- JSON data with nested structure analysis
- Parquet files for large datasets

Upload a file using the file upload panel to get started!

**Note**: This is a demo response. Configure the agent for real file analysis."""

        else:
            response = f"""🤖 **Hello {user_id}!**

I'm your AI Data Analyst assistant. I can help you with:

✅ **SQL Query Generation** - Convert natural language to SQL
✅ **Data Analysis** - Statistical insights and patterns
✅ **Visualizations** - Charts and graphs from your data
✅ **File Processing** - Upload and analyze CSV, Excel, JSON files
✅ **Machine Learning** - BigQuery ML model recommendations

Try asking me something like:
- "Show me the top 10 customers by revenue"
- "Create a chart of sales over time"
- "Analyze the uploaded dataset"

**Note**: This is a demo mode. Configure the Vertex AI agent for full functionality."""

        return {
            "response": response,
            "metadata": {
                "demo_mode": True,
                "user_id": user_id,
                "timestamp": aiplatform.utils.get_timestamp() if hasattr(aiplatform.utils, 'get_timestamp') else None,
                "message_type": "mock_response"
            }
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Check if the agent connection is healthy"""
        try:
            if not self.agent_full_name:
                return {
                    "status": "demo_mode",
                    "message": "Running in demo mode - no agent configured",
                    "agent_configured": False
                }
            
            # Try a simple ping to the agent
            test_input = {"message": "health_check", "test": True}
            request = aiplatform.QueryReasoningEngineRequest(
                name=self.agent_full_name,
                input=test_input
            )
            
            # This will raise an exception if the agent is not accessible
            response = self.client.query_reasoning_engine(request=request)
            
            return {
                "status": "healthy",
                "message": "Agent connection is working",
                "agent_configured": True,
                "agent_name": self.agent_name
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Agent connection failed: {str(e)}",
                "agent_configured": True,
                "error": str(e)
            } 