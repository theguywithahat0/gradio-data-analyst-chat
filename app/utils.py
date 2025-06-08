"""
Utility functions for file handling and exports

Handles file uploads, processing, and conversation exports.
"""

import os
import json
import csv
import tempfile
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileHandler:
    """Handles file uploads and processing"""
    
    def __init__(self):
        self.upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
        self.max_file_size = int(os.getenv("MAX_FILE_SIZE", "100")) * 1024 * 1024  # 100MB default
        self.allowed_extensions = {".csv", ".xlsx", ".xls", ".json", ".parquet", ".txt"}
        
        # Create upload directory
        os.makedirs(self.upload_dir, exist_ok=True)
        logger.info(f"Initialized FileHandler with upload dir: {self.upload_dir}")
    
    def process_upload(self, file_path: str, user_id: str) -> Dict[str, Any]:
        """Process an uploaded file and return metadata"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size:
                raise ValueError(f"File too large: {file_size} bytes (max: {self.max_file_size})")
            
            # Get file info
            file_name = os.path.basename(file_path)
            file_ext = Path(file_path).suffix.lower()
            
            # Check allowed extensions
            if file_ext not in self.allowed_extensions:
                raise ValueError(f"File type not allowed: {file_ext}")
            
            # Process based on file type
            metadata = self._analyze_file(file_path, file_ext)
            
            # Copy to user's upload directory
            user_upload_dir = os.path.join(self.upload_dir, user_id)
            os.makedirs(user_upload_dir, exist_ok=True)
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{timestamp}_{file_name}"
            dest_path = os.path.join(user_upload_dir, safe_filename)
            
            shutil.copy2(file_path, dest_path)
            
            result = {
                "filename": file_name,
                "safe_filename": safe_filename,
                "size": file_size,
                "file_type": file_ext,
                "upload_path": dest_path,
                "user_id": user_id,
                "timestamp": timestamp,
                **metadata
            }
            
            logger.info(f"Processed file upload: {file_name} for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing file upload: {e}")
            raise
    
    def _analyze_file(self, file_path: str, file_ext: str) -> Dict[str, Any]:
        """Analyze file content and return metadata"""
        try:
            if file_ext == ".csv":
                return self._analyze_csv(file_path)
            elif file_ext in [".xlsx", ".xls"]:
                return self._analyze_excel(file_path)
            elif file_ext == ".json":
                return self._analyze_json(file_path)
            elif file_ext == ".parquet":
                return self._analyze_parquet(file_path)
            elif file_ext == ".txt":
                return self._analyze_text(file_path)
            else:
                return {"columns": [], "row_count": 0, "sample_data": None}
                
        except Exception as e:
            logger.warning(f"Error analyzing file {file_path}: {e}")
            return {"columns": [], "row_count": 0, "sample_data": None, "analysis_error": str(e)}
    
    def _analyze_csv(self, file_path: str) -> Dict[str, Any]:
        """Analyze CSV file"""
        try:
            # Try to detect encoding
            encodings = ['utf-8', 'iso-8859-1', 'cp1252']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding, nrows=1000)  # Sample first 1000 rows
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                raise ValueError("Could not decode CSV file with any supported encoding")
            
            return {
                "columns": df.columns.tolist(),
                "row_count": len(df),
                "data_types": df.dtypes.to_dict(),
                "sample_data": df.head().to_dict("records") if len(df) > 0 else [],
                "null_counts": df.isnull().sum().to_dict()
            }
            
        except Exception as e:
            raise ValueError(f"Error analyzing CSV: {e}")
    
    def _analyze_excel(self, file_path: str) -> Dict[str, Any]:
        """Analyze Excel file"""
        try:
            # Read first sheet
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
            
            # Analyze first sheet
            df = pd.read_excel(file_path, sheet_name=sheet_names[0], nrows=1000)
            
            return {
                "columns": df.columns.tolist(),
                "row_count": len(df),
                "sheet_names": sheet_names,
                "active_sheet": sheet_names[0],
                "data_types": df.dtypes.to_dict(),
                "sample_data": df.head().to_dict("records") if len(df) > 0 else [],
                "null_counts": df.isnull().sum().to_dict()
            }
            
        except Exception as e:
            raise ValueError(f"Error analyzing Excel: {e}")
    
    def _analyze_json(self, file_path: str) -> Dict[str, Any]:
        """Analyze JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                df = pd.DataFrame(data[:1000])  # Sample first 1000 records
                return {
                    "columns": df.columns.tolist() if len(df) > 0 else [],
                    "row_count": len(data),
                    "data_types": df.dtypes.to_dict() if len(df) > 0 else {},
                    "sample_data": data[:5] if len(data) > 0 else [],
                    "structure": "array_of_objects"
                }
            elif isinstance(data, dict):
                return {
                    "columns": list(data.keys()),
                    "row_count": 1,
                    "sample_data": data,
                    "structure": "single_object"
                }
            else:
                return {
                    "columns": [],
                    "row_count": 1,
                    "sample_data": data,
                    "structure": "primitive"
                }
                
        except Exception as e:
            raise ValueError(f"Error analyzing JSON: {e}")
    
    def _analyze_parquet(self, file_path: str) -> Dict[str, Any]:
        """Analyze Parquet file"""
        try:
            df = pd.read_parquet(file_path)
            
            return {
                "columns": df.columns.tolist(),
                "row_count": len(df),
                "data_types": df.dtypes.to_dict(),
                "sample_data": df.head().to_dict("records") if len(df) > 0 else [],
                "null_counts": df.isnull().sum().to_dict()
            }
            
        except Exception as e:
            raise ValueError(f"Error analyzing Parquet: {e}")
    
    def _analyze_text(self, file_path: str) -> Dict[str, Any]:
        """Analyze text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            return {
                "columns": ["text"],
                "row_count": len(lines),
                "line_count": len(lines),
                "character_count": len(content),
                "sample_data": lines[:10]  # First 10 lines
            }
            
        except Exception as e:
            raise ValueError(f"Error analyzing text file: {e}")

class ExportManager:
    """Handles conversation and data exports"""
    
    def __init__(self):
        self.export_dir = os.getenv("EXPORT_DIR", "./exports")
        os.makedirs(self.export_dir, exist_ok=True)
        logger.info(f"Initialized ExportManager with export dir: {self.export_dir}")
    
    def export_conversation(
        self, 
        history: List[List[str]], 
        format: str, 
        user_id: str,
        session_id: str
    ) -> str:
        """Export conversation history in specified format"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chat_export_{user_id}_{session_id[:8]}_{timestamp}"
            
            if format.upper() == "JSON":
                return self._export_to_json(history, filename, user_id, session_id)
            elif format.upper() == "CSV":
                return self._export_to_csv(history, filename, user_id, session_id)
            elif format.upper() == "PDF":
                return self._export_to_pdf(history, filename, user_id, session_id)
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            logger.error(f"Error exporting conversation: {e}")
            raise
    
    def _export_to_json(self, history: List[List[str]], filename: str, user_id: str, session_id: str) -> str:
        """Export to JSON format"""
        try:
            export_data = {
                "export_info": {
                    "user_id": user_id,
                    "session_id": session_id,
                    "export_timestamp": datetime.now().isoformat(),
                    "format": "JSON",
                    "message_count": len(history)
                },
                "conversation": [
                    {
                        "message_id": i + 1,
                        "user_message": msg[0],
                        "agent_response": msg[1],
                        "timestamp": None  # Would need to be passed from history
                    }
                    for i, msg in enumerate(history)
                ]
            }
            
            filepath = os.path.join(self.export_dir, f"{filename}.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return filepath
            
        except Exception as e:
            raise ValueError(f"Error exporting to JSON: {e}")
    
    def _export_to_csv(self, history: List[List[str]], filename: str, user_id: str, session_id: str) -> str:
        """Export to CSV format"""
        try:
            filepath = os.path.join(self.export_dir, f"{filename}.csv")
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow([
                    "Message ID", 
                    "User Message", 
                    "Agent Response", 
                    "User ID", 
                    "Session ID"
                ])
                
                # Write data
                for i, msg in enumerate(history):
                    writer.writerow([
                        i + 1,
                        msg[0],
                        msg[1],
                        user_id,
                        session_id
                    ])
            
            return filepath
            
        except Exception as e:
            raise ValueError(f"Error exporting to CSV: {e}")
    
    def _export_to_pdf(self, history: List[List[str]], filename: str, user_id: str, session_id: str) -> str:
        """Export to PDF format"""
        try:
            # For PDF export, we'll create a simple HTML file and mention PDF conversion
            # In production, you might want to use libraries like reportlab or weasyprint
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Chat Export - {session_id[:8]}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ background-color: #f0f0f0; padding: 10px; margin-bottom: 20px; }}
                    .message {{ margin-bottom: 15px; padding: 10px; border: 1px solid #ddd; }}
                    .user {{ background-color: #e3f2fd; }}
                    .agent {{ background-color: #f3e5f5; }}
                    .timestamp {{ font-size: 0.8em; color: #666; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Chat Export</h1>
                    <p><strong>User:</strong> {user_id}</p>
                    <p><strong>Session:</strong> {session_id}</p>
                    <p><strong>Export Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>Messages:</strong> {len(history)}</p>
                </div>
            """
            
            for i, msg in enumerate(history):
                html_content += f"""
                <div class="message">
                    <div class="user">
                        <strong>User:</strong> {msg[0]}
                    </div>
                    <div class="agent">
                        <strong>Agent:</strong> {msg[1]}
                    </div>
                </div>
                """
            
            html_content += """
            </body>
            </html>
            """
            
            filepath = os.path.join(self.export_dir, f"{filename}.html")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Note: In production, you might convert this HTML to PDF
            # For now, we return the HTML file
            return filepath
            
        except Exception as e:
            raise ValueError(f"Error exporting to PDF/HTML: {e}")
    
    def cleanup_old_exports(self, days: int = 7) -> int:
        """Clean up export files older than specified days"""
        try:
            cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
            cleaned_count = 0
            
            for filename in os.listdir(self.export_dir):
                filepath = os.path.join(self.export_dir, filename)
                if os.path.isfile(filepath):
                    if os.path.getmtime(filepath) < cutoff_time:
                        os.remove(filepath)
                        cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} old export files")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up exports: {e}")
            return 0 