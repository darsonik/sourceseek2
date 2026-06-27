from b2sdk.v2 import InMemoryAccountInfo, B2Api
from app.core.config import settings

info = InMemoryAccountInfo()
b2_api = B2Api(info)

b2_api.authorize_account(
    application_key_id=settings.BLACKBLAZE_APPLICATION_KEY_ID,
    application_key=settings.BLACKBLAZE_APPLICATION_KEY
)

bucket = b2_api.get_bucket_by_name(settings.BLACKBLAZE_BUCKET_NAME)
print(f"Bucket name: {bucket.name}")

# Test upload
test_file = "test_b2.txt"
with open(test_file, "w") as f:
    f.write("Hello B2!")

try:
    print("Uploading...")
    uploaded = bucket.upload_local_file(
        local_file=test_file,
        file_name="test_folder/test_b2.txt"
    )
    print(f"Uploaded file id: {uploaded.id_}")
    
    # Test get file info
    print("Getting file info...")
    file_info = bucket.get_file_info_by_name("test_folder/test_b2.txt")
    print(f"File info: {file_info.id_}")
    
    # Test delete
    print("Deleting...")
    bucket.delete_file_version(file_info.id_, file_info.file_name)
    print("Deleted successfully.")
except Exception as e:
    print(f"Error: {e}")
