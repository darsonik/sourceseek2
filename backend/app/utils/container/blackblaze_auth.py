from b2sdk.v2 import KeepOrDeleteMode, CompareVersionMode, NewerFileSyncMode
from b2sdk.v2 import InMemoryAccountInfo
from b2sdk.v2 import B2Api
from app.core.config import settings

info = InMemoryAccountInfo()
b2_api = B2Api(info)

b2_api.authorize_account(
    application_key_id=settings.BLACKBLAZE_APPLICATION_KEY_ID,
    application_key=settings.BLACKBLAZE_APPLICATION_KEY
)

from b2sdk.v2 import ScanPoliciesManager
from b2sdk.v2 import parse_folder
from b2sdk.v2 import Synchronizer
from b2sdk.v2 import BasicSyncEncryptionSettingsProvider, EncryptionSettings, EncryptionMode
from b2sdk.v2 import SyncReport
import time
import sys

source='source_path/'
destination = f'b2://{settings.BLACKBLAZE_BUCKET_NAME}'

source_folder = parse_folder(source)
destination_folder = parse_folder(destination)

policy_manager = ScanPoliciesManager(exclude_all_symlinks=True)

synchronizer = Synchronizer(
    max_workers=10,
    sync_policy_manager=policy_manager,
    dry_run=False,
    allow_empty_source=True,
    compare_version_mode=CompareVersionMode.MODTIME,
    compare_threshold=3600,
    newer_file_mode=NewerFileSyncMode.REPLACE,
    keep_days_or_delete=KeepOrDeleteMode.KEEP_BEFORE_DELETE,
    keep_days=7
)

no_progress = False
encryption_settings_provider = BasicSyncEncryptionSettingsProvider(
    {f'{settings.BLACKBLAZE_BUCKET_NAME}' : EncryptionSettings(mode=EncryptionMode.SSE_B2)},
    {f'{settings.BLACKBLAZE_BUCKET_NAME}' : EncryptionSettings(mode=EncryptionMode.SSE_B2)}
)

with SyncReport(sys.stdout, no_progress=no_progress) as reporter:
    synchronizer.sync_folders(
        source_folder=source_folder,
        dest_folder=destination_folder,
        encryption_settings_provider=encryption_settings_provider,
        reporter=reporter,
        now_millis=int(round(time.time() * 1000)),

    )