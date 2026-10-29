import io
import tarfile
import pytest
from principia_legacy.backups import backup, restore, file_hash
from principia_legacy.common import write_json


def test_private_backup_round_trip_and_external_credentials(tmp_path):
    root = tmp_path / "data"
    write_json(root / "corpus/example.json", {"evidence": "original"})
    write_json(root / ".work/jobs/example.json", {"state": "unknown_possible_charge"})
    write_json(root / ".work/credentials.env", {"key": "not-in-backup"})
    result = backup(root, tmp_path / "backup.tar.gz")
    restored = tmp_path / "restored"
    report = restore(tmp_path / "backup.tar.gz", restored, result["sha256"])
    assert report["verified"] and (restored / ".work/jobs/example.json").exists()
    assert not (restored / ".work/credentials.env").exists()
    assert (restored / "corpus/example.json").read_bytes() == (
        root / "corpus/example.json"
    ).read_bytes()
    with pytest.raises(ValueError, match="must not exist"):
        restore(tmp_path / "backup.tar.gz", restored, result["sha256"])
    with pytest.raises(ValueError, match="checksum"):
        restore(tmp_path / "backup.tar.gz", tmp_path / "wrong", "0" * 64)


def test_restore_rejects_traversal_without_partial_destination(tmp_path):
    archive = tmp_path / "unsafe.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        member = tarfile.TarInfo("../escape")
        member.size = 1
        tar.addfile(member, io.BytesIO(b"x"))
    with pytest.raises(ValueError, match="Unsafe"):
        restore(archive, tmp_path / "destination", file_hash(archive))
    assert not (tmp_path / "escape").exists()
    assert not (tmp_path / "destination").exists()


def test_review_snapshot_excludes_authoring_caches_and_pins_release(tmp_path):
    root = tmp_path / "data"
    write_json(root / "manifests/releases/fixture.json", {"release_id": "fixture"})
    write_json(root / ".work/sources/private.json", {"text": "Private licensed source"})
    write_json(root / ".work/jobs/private.json", {"state": "succeeded"})
    result = backup(root, tmp_path / "review.tar.gz", review_release="fixture")
    destination = tmp_path / "review"
    report = restore(tmp_path / "review.tar.gz", destination, result["sha256"])
    assert report["review_release"] == "fixture"
    assert not (destination / ".work/sources").exists()
    assert not (destination / ".work/jobs").exists()
    with tarfile.open(tmp_path / "review.tar.gz") as archive:
        assert not any(name.startswith(".work/") for name in archive.getnames())
