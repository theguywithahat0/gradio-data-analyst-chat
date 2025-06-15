"""
Chat Handler for GCP Data Analyst Agent

Handles communication with the Vertex AI Reasoning Engine agent using the same approach as the verification script.
"""

import os
import vertexai
from vertexai import agent_engines
from google.adk.sessions import VertexAiSessionService
import logging
from typing import Dict, Any
import asyncio
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatHandler:
    """Handles communication with the deployed Vertex AI Agent Engine using VertexAiSessionService"""
    
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        self.agent_resource_name = os.getenv("AGENT_NAME")
        self.agent_engine = None
        self.session_service = None
        self.sessions = {}  # Store sessions per user

        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Vertex AI client and session service."""
        try:
            if not self.project_id or not self.agent_resource_name:
                raise ValueError("GCP environment variables not set correctly.")

            # Initialize Vertex AI
            vertexai.init(project=self.project_id, location=self.location)
            
            # Get agent engine
            self.agent_engine = agent_engines.get(self.agent_resource_name)
            
            # Create session service
            self.session_service = VertexAiSessionService(
                project=self.project_id, 
                location=self.location
            )
            
            logger.info(f"Successfully initialized agent: {self.agent_resource_name}")

        except Exception as e:
            logger.error(f"Failed to initialize ChatHandler: {e}")
            raise

    async def _get_or_create_session(self, user_id: str, session_id: str):
        """Get existing session or create a new one."""
        session_key = f"{user_id}:{session_id}"
        
        if session_key not in self.sessions:
            try:
                # Create new session
                session = await self.session_service.create_session(
                    app_name=self.agent_resource_name,
                    user_id=user_id,
                )
                self.sessions[session_key] = session
                logger.info(f"Created new session {session.id} for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to create session: {e}")
                raise
        
        return self.sessions[session_key]

    def send_message(
        self, 
        message: str, 
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Send a message to the agent using the same approach as the verification script.
        """
        try:
            # Run the async function
            return asyncio.run(self._send_message_async(message, user_id, session_id))
        except Exception as e:
            logger.error(f"Error in send_message: {e}")
            return {
                "response": f"❌ Error: {str(e)}",
                "metadata": {"error": True, "user_id": user_id, "session_id": session_id}
            }

    async def _send_message_async(self, message: str, user_id: str, session_id: str) -> Dict[str, Any]:
        """Async implementation of send_message."""
        full_response = ""
        
        try:
            if not self.agent_engine:
                raise RuntimeError("Agent not initialized. Check logs for errors.")

            logger.info(f"Querying agent for user {user_id} with: '{message}'...")
            
            # Get or create session
            session = await self._get_or_create_session(user_id, session_id)
            
            # Stream query to agent (same as verification script)
            response_parts = []
            for event in self.agent_engine.stream_query(
                user_id=user_id,
                session_id=session.id,
                message=message,
            ):
                logger.info(f"Received event: {event}")
                
                if "content" in event:
                    parts = event["content"].get("parts", [])
                    for part in parts:
                        if "text" in part:
                            response_parts.append(part["text"])
                            logger.info(f"Added text part: {part['text'][:100]}...")

            # Combine all response parts
            full_response = "".join(response_parts)

            logger.info(f"Successfully assembled full response for user {user_id}: '{full_response[:200]}...'")
            
            return {
                "response": full_response or "Agent returned an empty response.",
                "metadata": { 
                    "user_id": user_id, 
                    "session_id": session_id,
                    "vertex_session_id": session.id
                }
            }

        except Exception as e:
            logger.error(f"Error sending message to agent: {e}")
            error_message = f"❌ I'm having trouble processing your request right now. Error: {str(e)}"
            return {
                "response": error_message, 
                "metadata": {
                    "error": True, 
                    "user_id": user_id, 
                    "session_id": session_id
                }
            }

    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the agent connection."""
        if self.agent_engine and self.session_service:
            return {"status": "ok", "agent_resource_name": self.agent_resource_name}
        else:
            return {"status": "error", "message": "Agent or session service not initialized"} 