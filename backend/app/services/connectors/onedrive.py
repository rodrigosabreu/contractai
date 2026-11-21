"""OneDrive / Microsoft Graph connector service."""
import json
from typing import Any, Dict, List, Optional
from uuid import UUID

import msal
import requests
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.connector import Connector

settings = get_settings()


class OneDriveService:
    """OneDrive / Microsoft Graph connector for document sync."""
    
    def __init__(self, connector: Connector):
        self.connector = connector
        self.credentials = connector.credentials
        self.access_token: Optional[str] = None
        self._refresh_token_if_needed()
    
    def _refresh_token_if_needed(self) -> bool:
        """Refresh access token if expired or not present."""
        if self.access_token:
            return True
        
        refresh_token = self.credentials.get("refresh_token")
        if not refresh_token:
            return False
        
        app = msal.ConfidentialClientApplication(
            settings.MICROSOFT_CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}",
            client_credential=settings.MICROSOFT_CLIENT_SECRET,
        )
        
        result = app.acquire_token_by_refresh_token(
            self.credentials.get("refresh_token"),
            scopes=settings.MICROSOFT_SCOPES.split(","),
        )
        
        if "access_token" in result:
            self.access_token = result["access_token"]
            # Update stored credentials
            if "refresh_token" in result:
                self.credentials["refresh_token"] = result["refresh_token"]
            return True
        
        return False
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Graph API requests."""
        if not self._refresh_token_if_needed():
            raise Exception("Failed to refresh OneDrive access token")
        
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
    
    async def list_files(
        self,
        folder_id: Optional[str] = None,
        mime_types: Optional[List[str]] = None,
        top: int = 100,
    ) -> List[Dict[str, Any]]:
        """List files from OneDrive."""
        headers = self._get_headers()
        
        # Build query
        query_parts = []
        if folder_id:
            # Use folder ID to list children
            url = f"https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}/children"
        else:
            # Root folder
            url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
        
        # Add filter for file types if specified
        filter_parts = []
        if mime_types := [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
        ]:
            mime_filter = " or ".join([f"file/mimeType eq '{mt}'" for mt in [
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "text/plain",
            ]])
            url += f"?$filter={mime_filter}"
        
        url += "&$top=100"
        
        results = []
        next_url = url
        
        while next_url:
            response = requests.get(next_url, headers={
                "Authorization": f"Bearer {self.access_token}",
            })
            
            if response.status_code != 200:
                break
            
            data = response.json()
            items = data.get("value", [])
            
            for item in items:
                if "file" in item:  # Only files, not folders
                    results.append({
                        "id": item["id"],
                        "name": item["name"],
                        "mime_type": item["file"]["mimeType"],
                        "size": item["size"],
                        "modified_time": item["lastModifiedDateTime"],
                        "web_url": item["webUrl"],
                        "parent_id": item.get("parentReference", {}).get("id"),
                    })
            
            next_url = data.get("@odata.nextLink")
            if not next_url:
                break
        
        return results
    
    async def download_file(self, file_id: str) -> bytes:
        """Download file content from OneDrive."""
        headers = self._get_headers()
        
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/content"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"Failed to download file: {response.status_code}")
        
        return response.content
    
    async def sync(
        self,
        full_sync: bool = False,
        folder_id: Optional[str] = None,
        file_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Sync files from OneDrive.
        
        Args:
            full_sync: If True, sync all files; otherwise only new/modified
            folder_id: Specific folder to sync
            file_types: List of MIME types to sync
            
        Returns:
            Dict with sync results
        """
        files = await self.list_files(folder_id=folder_id)
        
        synced = 0
        errors = []
        
        for file_info in files:
            try:
                content = await self.download_file(file_info["id"])
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


async def get_onedrive_service(connector: Connector) -> OneDriveService:
    """Get OneDrive service instance."""
    return OneDriveService(connector)