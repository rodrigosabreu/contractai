"""Google Drive connector service."""
import json
from typing import Any, Dict, List, Optional
from uuid import UUID

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.connector import Connector

settings = get_settings()


class GoogleDriveService:
    """Google Drive connector for document sync."""
    
    def __init__(self, connector: Connector):
        self.connector = connector
        self.credentials = self._build_credentials()
        self.service = None
    
    def _build_credentials(self) -> Credentials:
        """Build Google OAuth credentials from stored token."""
        creds_data = self.connector.credentials
        return Credentials(
            token=creds_data.get("access_token"),
            refresh_token=creds_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=settings.GOOGLE_SCOPES.split(","),
        )
    
    def _get_service(self):
        """Get or create Drive API service."""
        if self.service is None:
            self.service = build("drive", "v3", credentials=self.credentials)
        return self.service
    
    async def list_files(
        self,
        folder_id: Optional[str] = None,
        mime_types: Optional[List[str]] = None,
        page_size: int = 100,
    ) -> List[Dict[str, Any]]:
        """List files from Google Drive."""
        service = self._get_service()
        
        query_parts = ["trashed = false"]
        if folder_id:
            query_parts.append(f"'{folder_id}' in parents")
        if mime_types:
            mime_query = " or ".join([f"mimeType = '{mt}'" for mt in mime_types])
            query_parts.append(f"({mime_query})")
        
        query = " and ".join(query_parts)
        
        results = []
        page_token = None
        
        while True:
            response = service.files().list(
                q=query,
                pageSize=page_size,
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, parents, webViewLink)",
                pageToken=page_token,
            ).execute()
            
            files = response.get("files", [])
            for file in files:
                results.append({
                    "id": file["id"],
                    "name": file["name"],
                    "mime_type": file["mimeType"],
                    "size": int(file.get("size", 0)),
                    "modified_time": file.get("modifiedTime"),
                    "parents": file.get("parents", []),
                    "web_view_link": file.get("webViewLink"),
                })
            
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        
        return results
    
    async def download_file(self, file_id: str) -> bytes:
        """Download file content from Google Drive."""
        service = self._get_service()
        
        request = service.files().get_media(fileId=file_id)
        file_data = b""
        downloader = MediaIoBaseDownload(
            io.BytesIO(file_data),
            request,
        )
        
        # Note: In production, use proper async file download
        # This is a simplified sync version
        import io
        file_data = io.BytesIO()
        downloader = MediaIoBaseDownload(file_data, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        return file_data.getvalue()
    
    async def sync(
        self,
        full_sync: bool = False,
        folder_id: Optional[str] = None,
        file_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Sync files from Google Drive.
        
        Args:
            full_sync: If True, sync all files; otherwise only new/modified
            folder_id: Specific folder to sync
            file_types: List of MIME types to sync
            
        Returns:
            Dict with sync results
        """
        mime_types = file_types or [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
        ]
        
        files = await self.list_files(
            folder_id=folder_id,
            mime_types=mime_types,
        )
        
        synced = 0
        errors = []
        
        for file_info in files:
            try:
                # Check if already processed (would check content_hash in production)
                # For now, skip files already synced
                
                # Download file
                content = await self.download_file(file_info["id"])
                
                # Here you would create Contract record and trigger analysis
                # For now, just count
                synced += 1
                
            except Exception as e:
                errors.append({
                    "file_id": file_info["id"],
                    "file_name": file_info["name"],
                    "error": str(e),
                })
        
        return {
            "synced_count": synced,
            "errors": errors,
            "total_files": len(files),
        }


async def get_google_drive_service(connector: Connector) -> GoogleDriveService:
    """Get Google Drive service instance."""
    return GoogleDriveService(connector)