from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient
from msgraph.generated.models.o_data_errors.o_data_error import ODataError
# Import other models as needed

from .config import settings

class GraphService:
    def __init__(self):
        if not all([settings.AZURE_AD_TENANT_ID, settings.AZURE_AD_CLIENT_ID, settings.AZURE_AD_CLIENT_SECRET]):
            raise ValueError("Azure AD credentials for Graph API are not configured.")
        
        credential = ClientSecretCredential(
            tenant_id=settings.AZURE_AD_TENANT_ID,
            client_id=settings.AZURE_AD_CLIENT_ID,
            client_secret=settings.AZURE_AD_CLIENT_SECRET
        )
        scopes = ['https://graph.microsoft.com/.default']
        self.graph_client = GraphServiceClient(credentials=credential, scopes=scopes)
        self.site_id = None 
        self.drive_id = None

    async def _initialize_sharepoint_ids(self):
        if self.site_id and self.drive_id:
            return
        try:
            # Note: Constructing site_path might need care. Using hostname and relative path.
            # Example: "yourtenant.sharepoint.com:/sites/YourSiteName"
            # Or if SHAREPOINT_SITE_NAME is "sites/YourSiteName", then "hostname:/SHAREPOINT_SITE_NAME"
            if not settings.SHAREPOINT_HOSTNAME or not settings.SHAREPOINT_SITE_NAME:
                 raise ValueError("SharePoint hostname or site name is not configured.")

            site_path_segment = settings.SHAREPOINT_SITE_NAME.strip('/')
            full_site_path = f"{settings.SHAREPOINT_HOSTNAME}:/{site_path_segment}"

            site = await self.graph_client.sites.by_site_path(site_path=full_site_path).get()
            if not site or not site.id:
                raise Exception(f"Could not retrieve site with path: {full_site_path}")
            self.site_id = site.id
            
            drives = await self.graph_client.sites.by_site_id(self.site_id).drives.get()
            if drives and drives.value:
                doc_lib_drive = next((drive for drive in drives.value if drive.name == settings.SHAREPOINT_DOCLIB_NAME), None)
                if doc_lib_drive and doc_lib_drive.id:
                    self.drive_id = doc_lib_drive.id
                else:
                    raise Exception(f"Document library '{settings.SHAREPOINT_DOCLIB_NAME}' not found in site '{settings.SHAREPOINT_SITE_NAME}'. Found drives: {[d.name for d in drives.value]}")
            else:
                raise Exception(f"No drives found for site '{settings.SHAREPOINT_SITE_NAME}'.")
        except ODataError as o_data_error:
            error_message = str(o_data_error.error.message) if o_data_error.error else "Unknown ODataError"
            # Log more details if available
            # print(f"Graph API ODataError during SharePoint ID initialization: {error_message}")
            # if o_data_error.error and o_data_error.error.details:
            #     for detail in o_data_error.error.details:
            #         print(f"  Code: {detail.code}, Message: {detail.message}")
            raise Exception(f"Graph API ODataError: {error_message}")
        except Exception as e:
            # print(f"Error initializing SharePoint IDs: {e}")
            raise

    async def upload_file(self, user_id: str, folder_name: str, file_name: str, file_content: bytes):
        if not self.drive_id: # Ensure drive_id is initialized
            await self._initialize_sharepoint_ids()
        # Placeholder: Actual upload logic to be detailed later.
        # Path example: root:/{user_id}/{folder_name}/{file_name}:/content
        # print(f"GraphService: Placeholder for uploading {file_name} to SharePoint for user {user_id} in folder {folder_name}.")
        pass

    async def list_user_folders(self, user_id: str):
        if not self.drive_id:
            await self._initialize_sharepoint_ids()
        # Placeholder
        # print(f"GraphService: Placeholder for listing folders for user {user_id}.")
        return []

    async def get_file_content(self, user_id: str, folder_identifier: str, file_path: str) -> tuple[bytes | None, str | None]:
        """
        Fetches file content and its guessed MIME type from SharePoint.
        folder_identifier: Could be a folder name or SharePoint ID.
        file_path: Relative path of the file within the folder_identifier.
        Returns: A tuple (file_bytes, mime_type_string) or (None, None) if not found.
        """
        if not self.drive_id: # Ensure drive_id is initialized
            await self._initialize_sharepoint_ids()
        
        full_sp_path = f"{user_id}/{folder_identifier}/{file_path}" # This path construction needs to be robust
        # print(f"GraphService: Conceptual - Attempting to get content for {full_sp_path} from SharePoint drive {self.drive_id}.")

        # TODO: Actual MS Graph API call to fetch file content based on full_sp_path
        # For example: GET /drives/{drive_id}/items/root:/{full_sp_path}:/content

        # Placeholder response:
        if file_path.endswith(".html") or file_path.endswith(".htm"):
            # print(f"GraphService: Conceptual - Serving HTML for {file_path}")
            return b"<html><body><h1>Placeholder HTML Content</h1></body></html>", "text/html"
        elif file_path.endswith(".css"):
            # print(f"GraphService: Conceptual - Serving CSS for {file_path}")
            return b"body { font-family: sans-serif; }", "text/css"
        elif file_path.endswith(".js"):
            # print(f"GraphService: Conceptual - Serving JS for {file_path}")
            return b"console.log('Placeholder JS loaded');", "application/javascript"
        elif file_path.endswith((".png", ".jpg", ".jpeg", ".gif")):
            # This would require actual image bytes; for now, just a placeholder concept
            # print(f"GraphService: Conceptual - Serving Image for {file_path}")
            return b"fake_image_bytes", "image/png" # Placeholder
        
        # print(f"GraphService: Conceptual - File not found or type not handled: {file_path}")
        return None, None

# It's generally better to manage the lifecycle of such services
# using FastAPI's dependency injection rather than a global singleton.
# So, we won't instantiate it here globally.
