from llama_index.readers.google import GoogleDriveReader
from googleapiclient.errors import HttpError
import time
from config import GDRIVE_RETRY_MAX_ATTEMPTS, GDRIVE_RETRY_BASE_DELAY, GDRIVE_REQUEST_DELAY


class RateLimitedGoogleDriveReader(GoogleDriveReader):
    """
    GoogleDriveReader with retry logic and rate limiting.

    Handles Google Drive API rate limits (HTTP 403 userRateLimitExceeded) by:
    - Retrying with exponential backoff (5s → 10s → 20s → 40s)
    - Adding configurable delays between requests
    - Re-raising non-rate-limit errors immediately
    """

    def load_data(self, **kwargs):
        """
        Override load_data with exponential backoff retry logic for rate limits.

        Returns:
            List of Document objects from Google Drive

        Raises:
            HttpError: If rate limit persists after max retries or for non-rate-limit errors
            Exception: For other errors (authentication, network, etc.)
        """
        for attempt in range(GDRIVE_RETRY_MAX_ATTEMPTS):
            try:
                # Add exponential backoff delay before retry attempts
                if attempt > 0:
                    delay = GDRIVE_RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    print(f"[gdrive] Rate limit hit. Retrying in {delay}s (attempt {attempt + 1}/{GDRIVE_RETRY_MAX_ATTEMPTS})...")
                    time.sleep(delay)

                # Call parent's load_data method
                docs = super().load_data(**kwargs)

                # Add small delay after successful call to prevent hitting limits
                if attempt > 0:  # Only if we had to retry
                    time.sleep(GDRIVE_REQUEST_DELAY)

                return docs

            except HttpError as e:
                # Check if it's a rate limit error (HTTP 403 with userRateLimitExceeded)
                is_rate_limit = (
                    e.resp.status == 403 and
                    'userRateLimitExceeded' in str(e)
                )

                if is_rate_limit:
                    # If this was the last attempt, re-raise the error
                    if attempt == GDRIVE_RETRY_MAX_ATTEMPTS - 1:
                        print(f"[gdrive] Rate limit persisted after {GDRIVE_RETRY_MAX_ATTEMPTS} attempts. Failing.")
                        raise
                    # Otherwise, continue to next retry
                    continue
                else:
                    # Not a rate limit error - re-raise immediately
                    raise

            except Exception as e:
                # Non-HTTP errors (auth, network, etc.) - re-raise immediately
                raise

        # Should never reach here due to raise in loop, but just in case
        raise RuntimeError("Retry logic failed unexpectedly")


def get_gdrive_reader(folder_id: str) -> RateLimitedGoogleDriveReader:
    """
    Returns a rate-limited GoogleDriveReader for the given folder ID.

    On first run this opens a browser for OAuth consent and saves token.json.
    Subsequent runs use the cached token silently.

    The returned reader automatically handles Google Drive API rate limits
    with exponential backoff retry logic.

    Args:
        folder_id: Google Drive folder ID to read from

    Returns:
        RateLimitedGoogleDriveReader instance configured for the folder
    """
    return RateLimitedGoogleDriveReader(
        credentials_path="credentials.json",
        token_path="token.json",
        folder_id=folder_id,
    )
