from pathlib import Path


def object_key(prefix: str, path: Path) -> str:
    name = path.name
    cleaned = prefix.strip("/")
    if not cleaned:
        return name
    return f"{cleaned}/{name}"


def store_exports(client, bucket: str, prefix: str, paths: list[Path]) -> list[str]:
    if not bucket:
        return []
    stored: list[str] = []
    for path in paths:
        key = object_key(prefix, path)
        client.upload_file(str(path), bucket, key)
        stored.append(key)
    return stored


def make_s3():
    import boto3

    return boto3.client("s3")
