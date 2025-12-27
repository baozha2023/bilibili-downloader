import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.version_manager import VersionManager

class TestVersionManager(unittest.TestCase):
    def setUp(self):
        self.mock_window = MagicMock()
        self.vm = VersionManager(self.mock_window)
        
    def test_git_available(self):
        print("\nChecking git availability...")
        available = self.vm.check_git_available()
        print(f"Git available: {available}")
        
    def test_get_current_version(self):
        print("\nGetting current version...")
        version = self.vm.get_current_version()
        print(f"Current version: {version}")
        self.assertIsNotNone(version)
        self.assertNotEqual(version, "未知")
        
    def test_get_versions(self):
        print("\nFetching remote versions...")
        # Note: This requires network access
        versions = self.vm.get_versions()
        print(f"Versions found: {versions}")
        self.assertIsInstance(versions, list)
        if versions:
            print(f"Latest version: {versions[0]}")
            
    @patch('subprocess.run')
    def test_switch_version_logic(self, mock_run):
        print("\nTesting switch version logic (Mocked)...")
        # Mock git checkout success
        mock_run.return_value.returncode = 0
        
        success, msg = self.vm.switch_version("v1.0.0")
        
        print(f"Switch result: {success}, {msg}")
        self.assertTrue(success)
        
        # Verify git checkout was called
        args, _ = mock_run.call_args
        self.assertIn('checkout', args[0])
        self.assertIn('v1.0.0', args[0])

if __name__ == '__main__':
    unittest.main()
