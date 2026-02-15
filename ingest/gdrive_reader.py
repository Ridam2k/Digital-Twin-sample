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
        Overridding load_data with exponential backoff retry logic due to rate limits
        """
        for attempt in range(GDRIVE_RETRY_MAX_ATTEMPTS):
            try:
                if attempt > 0:
                    delay = GDRIVE_RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    print(f"[gdrive] Rate limit hit. Retrying in {delay}s (attempt {attempt + 1}/{GDRIVE_RETRY_MAX_ATTEMPTS})...")
                    time.sleep(delay)

                # Call parent's load_data method
                docs = super().load_data(**kwargs)

                # Small delay after successful call to prevent hitting limits
                if attempt > 0:  #If we are retrying
                    time.sleep(GDRIVE_REQUEST_DELAY)

                return docs

            except HttpError as e:
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
                    raise

            except Exception as e:
                # Non-HTTP errors
                raise

        raise RuntimeError("Retry logic failed unexpectedly")


def get_gdrive_reader(folder_id: str) -> RateLimitedGoogleDriveReader:
    """
    Returns a rate-limited GoogleDriveReader for the given folder ID.

    First run -> opens a browser for OAuth consent and saves token.json
    Subsequent runs use the cached token 

    Returned reader automatically handles Google Drive API rate limits
    with exponential backoff retry logic
    """
    return RateLimitedGoogleDriveReader(
        credentials_path="credentials.json",
        token_path="token.json",
        folder_id=folder_id,
    )
