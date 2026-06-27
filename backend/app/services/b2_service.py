import os
from b2sdk.v2 import InMemoryAccountInfo, B2Api
from b2sdk.v2.exception import FileNotPresent
from app.core.config import settings

def get_b2_api() -> B2Api:
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    b2_api.authorize_account(
        "production",
        application_key_id=settings.BLACKBLAZE_APPLICATION_KEY_ID,
        application_key=settings.BLACKBLAZE_APPLICATION_KEY
    )
    return b2_api

def get_bucket():
    b2_api = get_b2_api()
    return b2_api.get_bucket_by_name(settings.BLACKBLAZE_BUCKET_NAME)

def get_remote_file_name(user_id: str, document_id: str, filename: str) -> str:
    """Generate a consistent remote file path to prevent collisions."""
    return f"user_{user_id}/{document_id}_{filename}"

def upload_file(local_path: str, user_id: str, document_id: str, filename: str) -> str:
    """
    Uploads a local file to Backblaze B2.
    Returns the file_id of the uploaded file.
    """
    bucket = get_bucket()
    remote_file_name = get_remote_file_name(user_id, document_id, filename)
    
    uploaded_file = bucket.upload_local_file(
        local_file=local_path,
        file_name=remote_file_name
    )
    return uploaded_file.id_

def download_file(user_id: str, document_id: str, filename: str, local_path: str) -> bool:
    """
    Downloads a file from Backblaze B2 to a local path.
    Returns True if successful, False if the file was not found.
    """
    bucket = get_bucket()
    remote_file_name = get_remote_file_name(user_id, document_id, filename)
    
    try:
        bucket.download_file_by_name(remote_file_name).save_to(local_path)
        return True
    except FileNotPresent:
        return False

def delete_file(user_id: str, document_id: str, filename: str) -> bool:
    """
    Deletes a file version from Backblaze B2.
    Returns True if deleted, False if it didn't exist.
    """
    bucket = get_bucket()
    remote_file_name = get_remote_file_name(user_id, document_id, filename)
    
    try:
        file_info = bucket.get_file_info_by_name(remote_file_name)
        bucket.delete_file_version(file_info.id_, remote_file_name)
        return True
    except FileNotPresent:
        return False
