"""
History Manager for Chat Conversations

Manages conversation history using Cloud Firestore for persistence.
"""

import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from google.cloud import firestore
from google.auth import default
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HistoryManager:
    """Manages conversation history and persistence"""
    
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.use_firestore = os.getenv("USE_FIRESTORE", "true").lower() == "true"
        
        # Collections
        self.conversations_collection = "chat_conversations"
        self.messages_collection = "chat_messages"
        
        # Initialize database
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize the database connection"""
        try:
            if self.use_firestore:
                # Initialize Firestore
                credentials, project = default()
                if not self.project_id:
                    self.project_id = project
                
                self.db = firestore.Client(
                    project=self.project_id,
                    credentials=credentials
                )
                logger.info(f"Initialized Firestore for project {self.project_id}")
            else:
                # Use local file-based storage for development
                self.db = None
                self.local_storage_dir = os.getenv("LOCAL_STORAGE_DIR", "./chat_history")
                os.makedirs(self.local_storage_dir, exist_ok=True)
                logger.info("Initialized local file storage for chat history")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            # Fallback to local storage
            self.use_firestore = False
            self.db = None
            self.local_storage_dir = "./chat_history"
            os.makedirs(self.local_storage_dir, exist_ok=True)
            logger.info("Falling back to local file storage")
    
    def save_conversation(
        self,
        user_id: str,
        session_id: str,
        user_message: str,
        agent_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save a conversation exchange"""
        try:
            timestamp = datetime.now(timezone.utc)
            
            conversation_data = {
                "user_id": user_id,
                "session_id": session_id,
                "user_message": user_message,
                "agent_response": agent_response,
                "timestamp": timestamp,
                "metadata": metadata or {}
            }
            
            if self.use_firestore and self.db:
                return self._save_to_firestore(conversation_data)
            else:
                return self._save_to_file(conversation_data)
                
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
            return False
    
    def _save_to_firestore(self, conversation_data: Dict[str, Any]) -> bool:
        """Save conversation to Firestore"""
        try:
            # Save to messages collection
            doc_ref = self.db.collection(self.messages_collection).add(conversation_data)
            
            # Update or create conversation metadata
            conversation_ref = self.db.collection(self.conversations_collection).document(
                f"{conversation_data['user_id']}_{conversation_data['session_id']}"
            )
            
            conversation_metadata = {
                "user_id": conversation_data["user_id"],
                "session_id": conversation_data["session_id"],
                "last_updated": conversation_data["timestamp"],
                "title": self._generate_conversation_title(conversation_data["user_message"]),
                "message_count": firestore.Increment(1)
            }
            
            conversation_ref.set(conversation_metadata, merge=True)
            
            logger.debug(f"Saved conversation to Firestore: {doc_ref[1].id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving to Firestore: {e}")
            return False
    
    def _save_to_file(self, conversation_data: Dict[str, Any]) -> bool:
        """Save conversation to local file"""
        try:
            # Convert datetime to string for JSON serialization
            conversation_data["timestamp"] = conversation_data["timestamp"].isoformat()
            
            user_dir = os.path.join(self.local_storage_dir, conversation_data["user_id"])
            os.makedirs(user_dir, exist_ok=True)
            
            session_file = os.path.join(user_dir, f"{conversation_data['session_id']}.json")
            
            # Load existing conversation or create new
            if os.path.exists(session_file):
                with open(session_file, 'r') as f:
                    conversation = json.load(f)
            else:
                conversation = {
                    "user_id": conversation_data["user_id"],
                    "session_id": conversation_data["session_id"],
                    "title": self._generate_conversation_title(conversation_data["user_message"]),
                    "created_at": conversation_data["timestamp"],
                    "messages": []
                }
            
            # Add new message
            conversation["messages"].append({
                "user_message": conversation_data["user_message"],
                "agent_response": conversation_data["agent_response"],
                "timestamp": conversation_data["timestamp"],
                "metadata": conversation_data["metadata"]
            })
            
            conversation["last_updated"] = conversation_data["timestamp"]
            
            # Save back to file
            with open(session_file, 'w') as f:
                json.dump(conversation, f, indent=2)
            
            logger.debug(f"Saved conversation to file: {session_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving to file: {e}")
            return False
    
    def get_recent_conversations(
        self, 
        user_id: str, 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent conversations for a user"""
        try:
            if self.use_firestore and self.db:
                return self._get_recent_from_firestore(user_id, limit)
            else:
                return self._get_recent_from_files(user_id, limit)
                
        except Exception as e:
            logger.error(f"Error getting recent conversations: {e}")
            return []
    
    def _get_recent_from_firestore(self, user_id: str, limit: int) -> List[Dict[str, Any]]:
        """Get recent conversations from Firestore"""
        try:
            conversations_ref = self.db.collection(self.conversations_collection)
            query = conversations_ref.where("user_id", "==", user_id)\
                                   .order_by("last_updated", direction=firestore.Query.DESCENDING)\
                                   .limit(limit)
            
            conversations = []
            for doc in query.stream():
                conv_data = doc.to_dict()
                conversations.append({
                    "session_id": conv_data["session_id"],
                    "title": conv_data.get("title", "Untitled Chat"),
                    "last_updated": conv_data["last_updated"],
                    "message_count": conv_data.get("message_count", 0)
                })
            
            return conversations
            
        except Exception as e:
            logger.error(f"Error getting conversations from Firestore: {e}")
            return []
    
    def _get_recent_from_files(self, user_id: str, limit: int) -> List[Dict[str, Any]]:
        """Get recent conversations from local files"""
        try:
            user_dir = os.path.join(self.local_storage_dir, user_id)
            
            if not os.path.exists(user_dir):
                return []
            
            conversations = []
            for filename in os.listdir(user_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(user_dir, filename)
                    try:
                        with open(filepath, 'r') as f:
                            conv_data = json.load(f)
                        
                        conversations.append({
                            "session_id": conv_data["session_id"],
                            "title": conv_data.get("title", "Untitled Chat"),
                            "last_updated": conv_data.get("last_updated", conv_data.get("created_at")),
                            "message_count": len(conv_data.get("messages", []))
                        })
                    except Exception as e:
                        logger.error(f"Error reading conversation file {filepath}: {e}")
                        continue
            
            # Sort by last_updated and limit
            conversations.sort(key=lambda x: x["last_updated"], reverse=True)
            return conversations[:limit]
            
        except Exception as e:
            logger.error(f"Error getting conversations from files: {e}")
            return []
    
    def get_conversation_messages(
        self, 
        user_id: str, 
        session_id: str
    ) -> List[Dict[str, Any]]:
        """Get all messages for a specific conversation"""
        try:
            if self.use_firestore and self.db:
                return self._get_messages_from_firestore(user_id, session_id)
            else:
                return self._get_messages_from_file(user_id, session_id)
                
        except Exception as e:
            logger.error(f"Error getting conversation messages: {e}")
            return []
    
    def _get_messages_from_firestore(self, user_id: str, session_id: str) -> List[Dict[str, Any]]:
        """Get messages from Firestore"""
        try:
            messages_ref = self.db.collection(self.messages_collection)
            query = messages_ref.where("user_id", "==", user_id)\
                               .where("session_id", "==", session_id)\
                               .order_by("timestamp")
            
            messages = []
            for doc in query.stream():
                msg_data = doc.to_dict()
                messages.append({
                    "user_message": msg_data["user_message"],
                    "agent_response": msg_data["agent_response"],
                    "timestamp": msg_data["timestamp"],
                    "metadata": msg_data.get("metadata", {})
                })
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting messages from Firestore: {e}")
            return []
    
    def _get_messages_from_file(self, user_id: str, session_id: str) -> List[Dict[str, Any]]:
        """Get messages from local file"""
        try:
            session_file = os.path.join(self.local_storage_dir, user_id, f"{session_id}.json")
            
            if not os.path.exists(session_file):
                return []
            
            with open(session_file, 'r') as f:
                conversation = json.load(f)
            
            return conversation.get("messages", [])
            
        except Exception as e:
            logger.error(f"Error getting messages from file: {e}")
            return []
    
    def delete_conversation(self, user_id: str, session_id: str) -> bool:
        """Delete a conversation and all its messages"""
        try:
            if self.use_firestore and self.db:
                return self._delete_from_firestore(user_id, session_id)
            else:
                return self._delete_from_file(user_id, session_id)
                
        except Exception as e:
            logger.error(f"Error deleting conversation: {e}")
            return False
    
    def _delete_from_firestore(self, user_id: str, session_id: str) -> bool:
        """Delete conversation from Firestore"""
        try:
            # Delete messages
            messages_ref = self.db.collection(self.messages_collection)
            query = messages_ref.where("user_id", "==", user_id)\
                               .where("session_id", "==", session_id)
            
            for doc in query.stream():
                doc.reference.delete()
            
            # Delete conversation metadata
            conversation_ref = self.db.collection(self.conversations_collection)\
                                     .document(f"{user_id}_{session_id}")
            conversation_ref.delete()
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting from Firestore: {e}")
            return False
    
    def _delete_from_file(self, user_id: str, session_id: str) -> bool:
        """Delete conversation from local file"""
        try:
            session_file = os.path.join(self.local_storage_dir, user_id, f"{session_id}.json")
            
            if os.path.exists(session_file):
                os.remove(session_file)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    def _generate_conversation_title(self, first_message: str, max_length: int = 50) -> str:
        """Generate a conversation title from the first message"""
        if not first_message:
            return "New Chat"
        
        # Clean and truncate the message
        title = first_message.strip()
        if len(title) > max_length:
            title = title[:max_length].rsplit(' ', 1)[0] + "..."
        
        return title or "New Chat" 