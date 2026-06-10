import os


def verify_download(path: str) -> bool:
    if not os.path.exists(path):
        return False

    size = os.path.getsize(path)
    if size == 0:
        return False

    return True
