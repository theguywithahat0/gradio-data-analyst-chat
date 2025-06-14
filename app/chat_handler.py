"""
Chat Handler for GCP Data Analyst Agent

Handles communication with the Vertex AI Reasoning Engine agent.
"""

import os
import vertexai
from vertexai import agent_engines
import logging
from typing import Dict, Any, Iterator
import json
import requests
import google.auth
import google.auth.transport.requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatHandler:
    """Handles communication with the deployed Vertex AI Agent Engine"""
    
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        self.agent_id = os.getenv("AGENT_NAME").split('/')[-1] # Extract from full resource name
        self.creds = None
        self.session = None

        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the HTTP client and get credentials."""
        try:
            if not self.project_id or not self.location or not self.agent_id:
                raise ValueError("GCP environment variables not set correctly.")

            # Get application default credentials
            self.creds, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            
            # Create a session with authorized credentials
            auth_req = google.auth.transport.requests.Request()
            self.creds.refresh(auth_req)
            self.session = requests.Session()
            self.session.headers.update({"Authorization": f"Bearer {self.creds.token}"})
            
            logger.info(f"Successfully initialized HTTP client for agent.")

        except Exception as e:
            logger.error(f"Failed to initialize ChatHandler: {e}")
            raise

    def send_message(
        self, 
        message: str, 
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Send a message to the agent via direct HTTP stream request.
        """
        full_response = ""
        api_endpoint = (
            f"https://{self.location}-aiplatform.googleapis.com/v1/projects/"
            f"{self.project_id}/locations/{self.location}/reasoningEngines/"
            f"{self.agent_id}:streamQuery?alt=sse"
        )
        
        payload = {
            "input": {
                "message": message,
                "user_id": user_id,
                "session_id": session_id
            }
        }
        
        try:
            logger.info(f"Querying agent at {api_endpoint} for user {user_id}...")
            
            with self.session.post(api_endpoint, json=payload, stream=True) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith('data: '):
                            try:
                                content = json.loads(decoded_line[len('data: '):])
                                logger.info(f"Received chunk: {content}")
                                if isinstance(content, dict) and "output" in content:
                                    full_response += content["output"]
                            except json.JSONDecodeError:
                                logger.warning(f"Could not decode JSON from line: {decoded_line}")


            logger.info(f"Successfully assembled full response for user {user_id}: '{full_response}'")
            return {
                "response": full_response or "Agent returned an empty response.",
                "metadata": { "user_id": user_id, "session_id": session_id }
            }

        except requests.exceptions.HTTPError as http_err:
            error_content = http_err.response.text
            logger.error(f"HTTP Error sending message to agent: {http_err} - {error_content}")
            error_message = f"❌ HTTP Error: {http_err}. Details: {error_content}"
            return {"response": error_message, "metadata": {"error": True}}
        except Exception as e:
            logger.error(f"Error sending message to agent: {e}")
            error_message = f"❌ I'm having trouble processing your request right now. Error: {str(e)}"
            return {"response": error_message, "metadata": {"error": True}}

    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the agent connection."""
        if self.session:
            return {"status": "ok", "agent_id": self.agent_id}
        else:
            return {"status": "error", "message": "HTTP session not initialized"} 