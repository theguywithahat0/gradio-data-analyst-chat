#!/usr/bin/env python3
"""
Data Analyst Chat Interface

A Gradio-based web interface for interacting with the GCP Data Analyst Agent.
"""

import gradio as gr
import os
from typing import List, Tuple, Optional, Dict, Any
import uuid
from dotenv import load_dotenv
import google.auth
import google.auth.transport.requests
import requests

from chat_handler import ChatHandler
from auth import AuthManager

# Load environment variables
load_dotenv()

# Configuration
TITLE = "🤖 Data Analyst Chat"
DESCRIPTION = """
Chat with our AI Data Analyst to get insights from your data. 
Ask questions in natural language and get SQL queries, visualizations, and analysis.
"""

# Initialize managers
chat_handler = ChatHandler()
auth_manager = AuthManager()

class DataAnalystChatApp:
    def __init__(self):
        self.current_user = None
        
    def authenticate_user(self, request: gr.Request) -> Optional[str]:
        """Extract user information from the request"""
        try:
            # Check if we're using IAP (production)
            if os.getenv("USE_IAP", "false").lower() == "true":
                user_email = request.headers.get("X-Goog-Authenticated-User-Email", "anonymous@example.com")
                self.current_user = user_email.replace("accounts.google.com:", "")
            else:
                # For local development, get the authenticated user from gcloud
                try:
                    creds, project = google.auth.default()
                    # Try to get user info from the credentials
                    if hasattr(creds, 'service_account_email'):
                        self.current_user = creds.service_account_email
                    else:
                        # For user credentials, we need to make a request to get user info
                        # Refresh credentials if needed
                        if not creds.valid:
                            auth_req = google.auth.transport.requests.Request()
                            creds.refresh(auth_req)
                        
                        # Get user info from Google's userinfo endpoint
                        response = requests.get(
                            'https://www.googleapis.com/oauth2/v1/userinfo',
                            headers={'Authorization': f'Bearer {creds.token}'}
                        )
                        if response.status_code == 200:
                            user_info = response.json()
                            self.current_user = user_info.get('email', 'unknown@example.com')
                        else:
                            self.current_user = os.getenv("MOCK_USER_EMAIL", "test@example.com")
                except Exception as auth_error:
                    print(f"Failed to get authenticated user: {auth_error}")
                    self.current_user = os.getenv("MOCK_USER_EMAIL", "test@example.com")
            
            return self.current_user
        except Exception as e:
            print(f"Auth error: {e}")
            return None
    
    def chat_response(
        self, 
        message: str, 
        history: List[Dict[str, str]], 
        session_id: str,
        request: gr.Request
    ) -> Tuple[List[Dict[str, str]], str, str]:
        """Handle chat messages and return response"""
        if not message.strip():
            return history, "", session_id
        
        # Authenticate user
        user = self.authenticate_user(request)
        if not user:
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": "❌ Authentication required"})
            return history, "", session_id
        
        try:
            # Get response from agent
            agent_response = chat_handler.send_message(
                message=message,
                user_id=user,
                session_id=session_id
            )
            
            # Add to history with new message format
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": agent_response["response"]})
            
            return history, "", session_id
            
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": error_msg})
            return history, "", session_id
    
    def clear_chat(self) -> Tuple[List, str, str]:
        """Clear the chat history"""
        return [], "", str(uuid.uuid4())

    def create_interface(self) -> gr.Blocks:
        """Create the Gradio interface"""
        with gr.Blocks(title=TITLE) as interface:
            # Header
            gr.Markdown(f"# {TITLE}")
            gr.Markdown(DESCRIPTION)
            
            # Chat interface
            chatbot = gr.Chatbot(
                label="Chat History",
                height=500,
                show_copy_button=True,
                type="messages"
            )
            
            # Input components
            with gr.Row():
                with gr.Column(scale=8):
                    msg = gr.Textbox(
                        label="Your Message",
                        placeholder="Ask a question...",
                        show_label=False
                    )
                with gr.Column(scale=1):
                    send = gr.Button("Send")
            
            # Session state
            session_id = gr.State(value=str(uuid.uuid4()))
            
            # Clear chat button
            clear = gr.Button("Clear")
            
            # Event handlers
            send.click(
                self.chat_response,
                inputs=[msg, chatbot, session_id],
                outputs=[chatbot, msg, session_id]
            )
            
            msg.submit(
                self.chat_response,
                inputs=[msg, chatbot, session_id],
                outputs=[chatbot, msg, session_id]
            )
            
            clear.click(
                self.clear_chat,
                outputs=[chatbot, msg, session_id]
            )
            
            return interface

def main():
    app = DataAnalystChatApp()
    interface = app.create_interface()
    interface.launch(
        server_name=os.getenv("HOST", "0.0.0.0"),
        server_port=int(os.getenv("PORT", 8080)),
        share=False
    )

if __name__ == "__main__":
    main() 