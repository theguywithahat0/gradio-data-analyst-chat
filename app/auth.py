"""
Authentication Manager for Google SSO

Handles authentication with Google Identity-Aware Proxy (IAP).
"""

import os
import json
from typing import Optional, Dict, Any
from google.auth import default
from google.auth.transport import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthManager:
    """Manages authentication and authorization"""
    
    def __init__(self):
        self.use_iap = os.getenv("USE_IAP", "true").lower() == "true"
        self.allowed_domains = os.getenv("ALLOWED_DOMAINS", "").split(",")
        self.allowed_domains = [d.strip() for d in self.allowed_domains if d.strip()]
        
        # Default to empty if no domains specified - must be configured
        if not self.allowed_domains:
            self.allowed_domains = []
        
        logger.info(f"Initialized AuthManager with allowed domains: {self.allowed_domains}")
    
    def extract_user_from_request(self, request) -> Optional[Dict[str, Any]]:
        """Extract user information from Gradio request"""
        try:
            if self.use_iap:
                return self._extract_from_iap(request)
            else:
                # Development mode - return mock user
                return self._get_mock_user()
                
        except Exception as e:
            logger.error(f"Error extracting user from request: {e}")
            return None
    
    def _extract_from_iap(self, request) -> Optional[Dict[str, Any]]:
        """Extract user information from Identity-Aware Proxy headers"""
        try:
            # IAP passes user information in headers
            user_email = request.headers.get("X-Goog-Authenticated-User-Email")
            user_id = request.headers.get("X-Goog-Authenticated-User-ID")
            
            if not user_email:
                logger.warning("No user email found in IAP headers")
                return None
            
            # Remove the accounts.google.com: prefix if present
            if user_email.startswith("accounts.google.com:"):
                user_email = user_email[len("accounts.google.com:"):]
            
            # Check if user domain is allowed
            if not self._is_domain_allowed(user_email):
                logger.warning(f"User domain not allowed: {user_email}")
                return None
            
            user_info = {
                "email": user_email,
                "user_id": user_id or user_email,
                "domain": user_email.split("@")[1] if "@" in user_email else "",
                "authenticated": True,
                "auth_method": "iap"
            }
            
            logger.info(f"Authenticated user via IAP: {user_email}")
            return user_info
            
        except Exception as e:
            logger.error(f"Error extracting user from IAP: {e}")
            return None
    
    def _get_mock_user(self) -> Dict[str, Any]:
        """Get a mock user for development"""
        mock_email = os.getenv("MOCK_USER_EMAIL", "developer@example.com")
        
        return {
            "email": mock_email,
            "user_id": mock_email,
            "domain": mock_email.split("@")[1] if "@" in mock_email else "example.com",
            "authenticated": True,
            "auth_method": "mock"
        }
    
    def _is_domain_allowed(self, email: str) -> bool:
        """Check if the user's email domain is allowed"""
        if not email or "@" not in email:
            return False
        
        domain = email.split("@")[1].lower()
        return domain in [d.lower() for d in self.allowed_domains]
    
    def is_user_authorized(self, user_info: Dict[str, Any]) -> bool:
        """Check if the user is authorized to use the application"""
        if not user_info or not user_info.get("authenticated"):
            return False
        
        # Check domain authorization
        if not self._is_domain_allowed(user_info.get("email", "")):
            return False
        
        # Additional authorization checks can be added here
        # For example: role-based access, specific user lists, etc.
        
        return True
    
    def get_user_permissions(self, user_info: Dict[str, Any]) -> Dict[str, bool]:
        """Get user permissions based on their profile"""
        if not user_info or not self.is_user_authorized(user_info):
            return {
                "can_chat": False,
                "can_upload_files": False,
                "can_export": False,
                "can_view_history": False
            }
        
        # For now, all authorized users get all permissions
        # This can be extended for role-based access
        return {
            "can_chat": True,
            "can_upload_files": True,
            "can_export": True,
            "can_view_history": True
        }
    
    def create_audit_log(
        self, 
        user_info: Dict[str, Any], 
        action: str, 
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create an audit log entry"""
        return {
            "user_email": user_info.get("email"),
            "user_id": user_info.get("user_id"),
            "action": action,
            "details": details or {},
            "timestamp": "",  # Will be set by the logging system
            "auth_method": user_info.get("auth_method")
        } 