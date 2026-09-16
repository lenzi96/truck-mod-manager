"""
Unit tests for GitHub Updater backend and version comparison.
"""

import os
import tarfile
import tempfile
import unittest
import zipfile

from truck_mod_manager.core.github_updater import (
    GitHubUpdateInfo,
    UpdateStep,
    compare_versions,
    get_github_repo,
    get_github_token,
    is_valid_archive,
    set_github_repo,
    set_github_token,
)


class TestGitHubUpdater(unittest.TestCase):
    def test_compare_versions(self):
        # Newer remote version available
        self.assertLess(compare_versions("1.0.0", "1.0.1"), 0)
        self.assertLess(compare_versions("1.0.0", "1.1.0"), 0)
        self.assertLess(compare_versions("1.9.9", "2.0.0"), 0)
        self.assertLess(compare_versions("v1.0.0", "v1.2.0"), 0)
        self.assertLess(compare_versions("1.0.0", "v2.0.0"), 0)

        # Equal versions
        self.assertEqual(compare_versions("1.0.0", "1.0.0"), 0)
        self.assertEqual(compare_versions("v1.5.0", "1.5.0"), 0)
        self.assertEqual(compare_versions("v1.5.0", "v1.5.0"), 0)

        # Older remote version (local is newer / dev)
        self.assertGreater(compare_versions("1.1.0", "1.0.9"), 0)
        self.assertGreater(compare_versions("2.0.0", "1.9.9"), 0)
        self.assertGreater(compare_versions("v2.0.1", "1.9.0"), 0)

    def test_repo_normalization_and_setting(self):
        original_repo = get_github_repo()
        try:
            # Set plain owner/repo
            set_github_repo("testuser/testrepo")
            self.assertEqual(get_github_repo(), "testuser/testrepo")

            # Set full https url with .git
            set_github_repo("https://github.com/customowner/customrepo.git")
            self.assertEqual(get_github_repo(), "customowner/customrepo")

            # Set git url
            set_github_repo("git@github.com:anotherowner/anotherrepo.git")
            self.assertEqual(get_github_repo(), "anotherowner/anotherrepo")
        finally:
            set_github_repo(original_repo)

    def test_token_setting(self):
        original_token = get_github_token() or ""
        try:
            test_token = "ghp_test_token_1234567890abcdef"
            set_github_token(test_token)
            self.assertEqual(get_github_token(), test_token)
        finally:
            set_github_token(original_token)

    def test_update_info_defaults(self):
        info = GitHubUpdateInfo()
        self.assertIsNotNone(info.installed_version)
        self.assertEqual(info.remote_version, "Unbekannt")
        self.assertFalse(info.has_update)
        self.assertFalse(info.github_auth_error)
        self.assertEqual(info.release_notes, "")

    def test_update_step_dataclass(self):
        step = UpdateStep(
            name="Test Step",
            command=["echo", "hello"],
            description="Testing update step",
        )
        self.assertEqual(step.name, "Test Step")
        self.assertEqual(step.command, ["echo", "hello"])
        self.assertEqual(step.description, "Testing update step")

    def test_is_valid_archive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Invalid/empty file
            empty_file = os.path.join(tmpdir, "empty.bin")
            with open(empty_file, "wb") as f:
                f.write(b"")
            self.assertIsNone(is_valid_archive(empty_file))

            # Valid tar.gz with uncompressible random data
            tar_file = os.path.join(tmpdir, "test.tar.gz")
            sample_content = os.path.join(tmpdir, "sample.bin")
            with open(sample_content, "wb") as f:
                f.write(os.urandom(2000))
            with tarfile.open(tar_file, "w:gz") as tar:
                tar.add(sample_content, arcname="sample.bin")
            self.assertEqual(is_valid_archive(tar_file), "tar")

            # Valid zip
            zip_file = os.path.join(tmpdir, "test.zip")
            with zipfile.ZipFile(zip_file, "w") as zf:
                zf.writestr("sample.bin", os.urandom(2000))
            self.assertEqual(is_valid_archive(zip_file), "zip")


if __name__ == "__main__":
    unittest.main()
