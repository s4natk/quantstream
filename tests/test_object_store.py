from pathlib import Path

from quantstream.object_store import object_key, store_exports


class FakeS3:
    def __init__(self):
        self.uploads = []

    def upload_file(self, filename, bucket, key):
        self.uploads.append((filename, bucket, key))


def test_object_key_joins_the_prefix():
    key = object_key("candles", Path("archives/2026-09-21.parquet"))
    assert key == "candles/2026-09-21.parquet"
    assert object_key("/", Path("2026-09-21.parquet")) == "2026-09-21.parquet"


def test_store_exports_uploads_each_file():
    client = FakeS3()
    paths = [Path("archives/2026-09-21.parquet"), Path("archives/2026-09-22.parquet")]
    stored = store_exports(client, "quantstream-archive", "candles", paths)
    assert stored == ["candles/2026-09-21.parquet", "candles/2026-09-22.parquet"]
    assert client.uploads[0][1] == "quantstream-archive"


def test_empty_bucket_skips_upload():
    client = FakeS3()
    assert store_exports(client, "", "candles", [Path("a.parquet")]) == []
    assert client.uploads == []
