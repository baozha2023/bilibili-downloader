import sys
import os
import logging
import shutil

# Add current directory to path
sys.path.append(os.getcwd())

from core.version_manager import VersionManager

# Setup logging
logging.basicConfig(level=logging.INFO)

class TestVersionManager(VersionManager):
    def _apply_update(self, new_dir, temp_root):
        print(f"MOCK: _apply_update called with new_dir={new_dir}, temp_root={temp_root}")
        if os.path.exists(os.path.join(new_dir, 'bilibili_downloader.exe')):
            print("SUCCESS: Found bilibili_downloader.exe in extracted dir")
            return True, "Mock Success"
        else:
            print("FAILURE: bilibili_downloader.exe not found")
            return False, "Mock Failure"
            
    def cleanup(self, temp_root):
        if os.path.exists(temp_root):
            shutil.rmtree(temp_root)
            print(f"Cleaned up {temp_root}")

def test_github_versions():
    vm = TestVersionManager(None)
    print("Fetching GitHub versions...")
    versions = vm.get_versions(VersionManager.SOURCE_GITHUB)
    
    print(f"Found {len(versions)} versions.")
    
    v53 = None
    for v in versions:
        if v['tag'] == 'v5.3':
            v53 = v
            break
            
    if v53:
        print(f"\nFound v5.3: {v53['tag']}")
        print("Checking v5.3 assets...")
        assets = v53.get('assets')
        if assets is None:
            print("Assets is None, trying to fetch via HTML fallback...")
            assets = vm._fetch_github_assets_html('v5.3')
            
        print(f"v5.3 Assets: {assets}")
        
        target_asset = None
        if assets:
            for asset in assets:
                if asset.get('name', '').endswith('.zip') and 'bilibili_downloader' in asset.get('name', ''):
                    target_asset = asset
                    break
            if not target_asset:
                 for asset in assets:
                    if asset.get('name', '').endswith('.zip'):
                        target_asset = asset
                        break
        
        if target_asset:
            print(f"SUCCESS: Found zip asset for v5.3: {target_asset['name']}")
            print(f"URL: {target_asset['browser_download_url']}")
            
            print("\nTesting download and extract...")
            # This calls _download_and_extract_zip -> _apply_update (mocked)
            success, msg = vm._download_and_extract_zip(target_asset['browser_download_url'])
            print(f"Download Result: success={success}, msg={msg}")
            
        else:
            print("FAILURE: No zip asset found for v5.3")
    else:
        print("FAILURE: v5.3 not found")

if __name__ == "__main__":
    test_github_versions()
