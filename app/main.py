#!/usr/bin/env python3
"""
Data Analyst Chat Interface

A Gradio-based web interface for interacting with the GCP Data Analyst Agent.
Provides chat functionality, file uploads, result exports, and conversation history.
"""

import gradio as gr
import pandas as pd
import json
import os
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
import uuid

from chat_handler import ChatHandler
from history import HistoryManager
from auth import AuthManager
from utils import FileHandler, ExportManager

# Configuration
TITLE = "🤖 Data Analyst Chat"
DESCRIPTION = """
Chat with our AI Data Analyst to get insights from your data. 
Ask questions in natural language and get SQL queries, visualizations, and analysis.
"""

# Initialize managers
chat_handler = ChatHandler()
history_manager = HistoryManager()
auth_manager = AuthManager()
file_handler = FileHandler()
export_manager = ExportManager()

class DataAnalystChatApp:
    def __init__(self):
        self.current_user = None
        self.current_session_id = str(uuid.uuid4())
        
    def authenticate_user(self, request: gr.Request) -> Optional[str]:
        """Extract user information from the request"""
        try:
            # In production with IAP, user info will be in headers
            user_email = request.headers.get("X-Goog-Authenticated-User-Email", "anonymous@example.com")
            self.current_user = user_email.replace("accounts.google.com:", "")
            return self.current_user
        except Exception as e:
            print(f"Auth error: {e}")
            return None
    
    def chat_response(
        self, 
        message: str, 
        history: List[List[str]], 
        request: gr.Request
    ) -> Tuple[List[List[str]], str]:
        """Handle chat messages and return response"""
        if not message.strip():
            return history, ""
        
        # Authenticate user
        user = self.authenticate_user(request)
        if not user:
            history.append([message, "❌ Authentication required"])
            return history, ""
        
        try:
            # Get response from agent
            agent_response = chat_handler.send_message(
                message=message,
                user_id=user,
                session_id=self.current_session_id
            )
            
            # Add to history
            history.append([message, agent_response["response"]])
            
            # Save conversation history
            history_manager.save_conversation(
                user_id=user,
                session_id=self.current_session_id,
                user_message=message,
                agent_response=agent_response["response"],
                metadata=agent_response.get("metadata", {})
            )
            
            return history, ""
            
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            history.append([message, error_msg])
            return history, ""
    
    def upload_file(
        self, 
        file: gr.File, 
        request: gr.Request
    ) -> Tuple[str, str]:
        """Handle file uploads for data analysis"""
        user = self.authenticate_user(request)
        if not user:
            return "❌ Authentication required", ""
        
        if not file:
            return "❌ No file uploaded", ""
        
        try:
            # Process the uploaded file
            result = file_handler.process_upload(
                file_path=file.name,
                user_id=user
            )
            
            # Generate analysis prompt
            analysis_prompt = f"""I've uploaded a file: {result['filename']}
            
File info:
- Size: {result['size']} bytes
- Type: {result['file_type']}
- Columns: {', '.join(result.get('columns', []))}
- Rows: {result.get('row_count', 'N/A')}

Please analyze this data and provide insights."""

            return "✅ File uploaded successfully!", analysis_prompt
            
        except Exception as e:
            return f"❌ Upload failed: {str(e)}", ""
    
    def export_conversation(
        self, 
        history: List[List[str]], 
        format: str,
        request: gr.Request
    ) -> gr.File:
        """Export conversation history"""
        user = self.authenticate_user(request)
        if not user:
            return None
        
        try:
            export_path = export_manager.export_conversation(
                history=history,
                format=format,
                user_id=user,
                session_id=self.current_session_id
            )
            return gr.File(export_path)
        except Exception as e:
            print(f"Export error: {e}")
            return None
    
    def load_conversation_history(
        self, 
        request: gr.Request
    ) -> List[Tuple[str, str]]:
        """Load recent conversation history for the user"""
        user = self.authenticate_user(request)
        if not user:
            return []
        
        try:
            conversations = history_manager.get_recent_conversations(
                user_id=user,
                limit=20
            )
            return [(conv["title"], conv["session_id"]) for conv in conversations]
        except Exception as e:
            print(f"History load error: {e}")
            return []
    
    def load_specific_conversation(
        self, 
        session_id: str,
        request: gr.Request
    ) -> List[List[str]]:
        """Load a specific conversation by session ID"""
        user = self.authenticate_user(request)
        if not user:
            return []
        
        try:
            messages = history_manager.get_conversation_messages(
                user_id=user,
                session_id=session_id
            )
            return [[msg["user_message"], msg["agent_response"]] for msg in messages]
        except Exception as e:
            print(f"Conversation load error: {e}")
            return []
    
    def clear_chat(self) -> Tuple[List, str]:
        """Clear current chat and start new session"""
        self.current_session_id = str(uuid.uuid4())
        return [], ""
    
    def create_interface(self) -> gr.Blocks:
        """Create the Gradio interface"""
        with gr.Blocks(
            title=TITLE,
            theme=gr.themes.Soft(),
            css="""
            .gradio-container {
                max-width: 1200px !important;
            }
            .chat-container {
                height: 600px !important;
            }
            """
        ) as interface:
            
            gr.Markdown(f"# {TITLE}")
            gr.Markdown(DESCRIPTION)
            
            with gr.Row():
                with gr.Column(scale=3):
                    # Main chat interface
                    chatbot = gr.Chatbot(
                        label="Data Analyst Chat",
                        height=500,
                        container=True,
                        elem_classes=["chat-container"]
                    )
                    
                    with gr.Row():
                        msg_input = gr.Textbox(
                            placeholder="Ask me anything about your data...",
                            label="Your message",
                            lines=2,
                            scale=4
                        )
                        send_btn = gr.Button("Send", variant="primary", scale=1)
                    
                    with gr.Row():
                        clear_btn = gr.Button("🗑️ New Chat", variant="secondary")
                        export_btn = gr.Button("📥 Export Chat", variant="secondary")
                
                with gr.Column(scale=1):
                    # File upload section
                    gr.Markdown("### 📁 File Upload")
                    file_upload = gr.File(
                        label="Upload data file",
                        file_types=[".csv", ".xlsx", ".json", ".parquet"],
                        type="filepath"
                    )
                    upload_status = gr.Textbox(
                        label="Upload Status",
                        interactive=False,
                        lines=2
                    )
                    
                    # Export options
                    gr.Markdown("### 📊 Export Options")
                    export_format = gr.Radio(
                        choices=["JSON", "CSV", "PDF"],
                        value="JSON",
                        label="Export Format"
                    )
                    export_file = gr.File(label="Download Export")
                    
                    # Conversation history
                    gr.Markdown("### 📜 Recent Conversations")
                    history_dropdown = gr.Dropdown(
                        label="Load Previous Chat",
                        choices=[],
                        interactive=True
                    )
                    load_history_btn = gr.Button("Load Chat", variant="secondary")
            
            # Event handlers
            msg_input.submit(
                fn=self.chat_response,
                inputs=[msg_input, chatbot],
                outputs=[chatbot, msg_input]
            ).then(
                fn=lambda: gr.update(choices=self.load_conversation_history(gr.Request())),
                outputs=[history_dropdown]
            )
            
            send_btn.click(
                fn=self.chat_response,
                inputs=[msg_input, chatbot],
                outputs=[chatbot, msg_input]
            ).then(
                fn=lambda: gr.update(choices=self.load_conversation_history(gr.Request())),
                outputs=[history_dropdown]
            )
            
            file_upload.upload(
                fn=self.upload_file,
                inputs=[file_upload],
                outputs=[upload_status, msg_input]
            )
            
            export_btn.click(
                fn=self.export_conversation,
                inputs=[chatbot, export_format],
                outputs=[export_file]
            )
            
            clear_btn.click(
                fn=self.clear_chat,
                outputs=[chatbot, msg_input]
            ).then(
                fn=lambda: gr.update(choices=self.load_conversation_history(gr.Request())),
                outputs=[history_dropdown]
            )
            
            load_history_btn.click(
                fn=self.load_specific_conversation,
                inputs=[history_dropdown],
                outputs=[chatbot]
            )
            
            # Load conversation history on startup
            interface.load(
                fn=self.load_conversation_history,
                outputs=[history_dropdown]
            )
        
        return interface

def main():
    """Main application entry point"""
    app = DataAnalystChatApp()
    interface = app.create_interface()
    
    # Launch configuration
    port = int(os.getenv("PORT", 7860))
    host = os.getenv("HOST", "0.0.0.0")
    
    interface.launch(
        server_name=host,
        server_port=port,
        share=False,
        auth=None,  # Auth handled by Google IAP in production
        show_error=True,
        favicon_path=None
    )

if __name__ == "__main__":
    main() 