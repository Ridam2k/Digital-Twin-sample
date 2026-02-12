from llama_index.readers.google import GoogleDriveReader


def get_gdrive_reader(folder_id: str) -> GoogleDriveReader:
    """
    Returns a GoogleDriveReader for the given folder ID.
    On first run this opens a browser for OAuth consent and saves token.json.
    Subsequent runs use the cached token silently.
    """
    return GoogleDriveReader(
        credentials_path="credentials.json",
        token_path="token.json",
        folder_id=folder_id,
    )
