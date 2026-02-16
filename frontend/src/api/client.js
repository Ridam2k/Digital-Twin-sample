/**
 * API client for Digital Twin backend.
 * Handles HTTP communication with the FastAPI server.
 */

const API_BASE_URL = 'http://localhost:8000';

/**
 * Custom error class for API-specific errors.
 */
export class APIError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Send a query to the backend and get a response.
 *
 * @param {string} queryText - The user's question
 * @param {string|null} contentType - Optional content type filter (e.g., "code")
 * @returns {Promise<Object>} Response object with {response, citations, mode, router_scores, out_of_scope}
 * @throws {APIError} If the request fails
 */
export async function sendQuery(queryText, contentType = null, history = []) {
  const response = await fetch(`${API_BASE_URL}/api/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: queryText,
      ...(contentType && { content_type: contentType }),
      history,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new APIError(
      `API request failed: ${response.status}`,
      response.status,
      errorData.detail || 'Unknown error'
    );
  }

  return response.json();
}

/**
 * Stream a query and receive progressive updates via Server-Sent Events (SSE).
 * Returns response immediately, then streams metrics as they complete in the background.
 *
 * @param {string} queryText - The user's question
 * @param {string|null} contentType - Optional content type filter (e.g., "code")
 * @param {Object} callbacks - Event handlers for different stream events
 * @param {Function} callbacks.onResponse - Called when response arrives (data: {response, citations, mode, ...})
 * @param {Function} callbacks.onMetrics - Called when metrics arrive (optional, for logging)
 * @param {Function} callbacks.onDone - Called when stream completes
 * @param {Function} callbacks.onError - Called on error
 * @throws {APIError} If the request fails
 */
export async function streamQuery(queryText, contentType, callbacks, history = []) {
  const url = `${API_BASE_URL}/api/query/stream`;

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: queryText,
      ...(contentType && { content_type: contentType }),
      history,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new APIError(
      `API request failed: ${response.status}`,
      response.status,
      errorData.detail || 'Unknown error'
    );
  }

  // Read SSE stream
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      // Decode chunk and add to buffer
      buffer += decoder.decode(value, { stream: true });

      // Split by newlines (SSE format uses \n\n as delimiter)
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const eventData = JSON.parse(line.slice(6));

          switch (eventData.type) {
            case 'response':
              callbacks.onResponse?.(eventData.data);
              break;

            case 'metrics_groundedness':
            case 'metrics_persona':
              // Metrics are logged server-side, optionally notify frontend
              callbacks.onMetrics?.(eventData.data);
              break;

            case 'done':
              callbacks.onDone?.();
              break;

            case 'error':
              throw new APIError(
                eventData.data.message,
                500,
                eventData.data.message
              );
          }
        }
      }
    }
  } catch (error) {
    callbacks.onError?.(error);
    throw error;
  }
}

/**
 * Check backend health status.
 *
 * @returns {Promise<Object>} Health status object
 */
export async function checkHealth() {
  const response = await fetch(`${API_BASE_URL}/health`);
  return response.json();
}

/**
 * Fetch evaluation metrics (groundedness, persona scores).
 *
 * @param {string} namespace - Optional filter by namespace
 * @param {number} limit - Number of recent entries to include
 * @returns {Promise<Object>} Metrics summary and recent entries
 * @throws {APIError} If the request fails
 */
export async function fetchEvalMetrics(namespace = null, limit = 50) {
  let url = `${API_BASE_URL}/api/eval/metrics?limit=${limit}`;
  if (namespace) {
    url += `&namespace=${namespace}`;
  }

  const response = await fetch(url);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new APIError(
      `Failed to fetch eval metrics: ${response.status}`,
      response.status,
      errorData.detail || 'Unknown error'
    );
  }

  return response.json();
}

/**
 * Fetch retrieval statistics (Recall@K, MRR@K).
 *
 * @param {boolean} recompute - Force recomputation (bypass cache)
 * @param {number} k - K value for Recall@K and MRR@K
 * @returns {Promise<Object>} Retrieval stats
 * @throws {APIError} If the request fails
 */
export async function fetchRetrievalStats(recompute = false, k = 5) {
  const url = `${API_BASE_URL}/api/eval/retrieval-stats?k=${k}&recompute=${recompute}`;
  const response = await fetch(url);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new APIError(
      `Failed to fetch retrieval stats: ${response.status}`,
      response.status,
      errorData.detail || 'Unknown error'
    );
  }

  return response.json();
}

/**
 * Fetch available projects (unique doc_title values) from Qdrant.
 *
 * @returns {Promise<Object>} Projects payload with {groups, total_unique, collection}
 * @throws {APIError} If the request fails
 */
export async function fetchProjects() {
  const response = await fetch(`${API_BASE_URL}/api/projects`);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new APIError(
      `Failed to fetch projects: ${response.status}`,
      response.status,
      errorData.detail || 'Unknown error'
    );
  }

  return response.json();
}

/**
 * Fetch database statistics (chunk/document counts).
 *
 * @returns {Promise<Object>} Database stats
 * @throws {APIError} If the request fails
 */
export async function fetchDbStats() {
  const url = `${API_BASE_URL}/api/eval/db-stats`;
  const response = await fetch(url);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new APIError(
      `Failed to fetch DB stats: ${response.status}`,
      response.status,
      errorData.detail || 'Unknown error'
    );
  }

  return response.json();
}

/**
 * Fetch chunk similarity statistics.
 *
 * @param {number} limit - Number of recent queries to analyze
 * @returns {Promise<Object>} Similarity stats and distribution
 * @throws {APIError} If the request fails
 */
export async function fetchSimilarityStats(limit = 100) {
  const url = `${API_BASE_URL}/api/eval/similarity-stats?limit=${limit}`;
  const response = await fetch(url);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new APIError(
      `Failed to fetch similarity stats: ${response.status}`,
      response.status,
      errorData.detail || 'Unknown error'
    );
  }

  return response.json();
}

/**
 * Trigger Google Drive ingestion (both technical and non-technical).
 *
 * @returns {Promise<Object>} Ingestion result with statistics
 * @throws {APIError} If the request fails
 */
export async function ingestGoogleDrive() {
  const response = await fetch(`${API_BASE_URL}/api/ingest/gdrive`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new APIError(
      `Google Drive ingestion failed: ${response.status}`,
      response.status,
      errorData.detail || 'Unknown error'
    );
  }

  return response.json();
}

/**
 * Trigger GitHub ingestion for configured repositories.
 *
 * @param {Array<string>|null} customRepos - Optional array of custom repos to ingest (e.g., ["owner/repo"])
 * @returns {Promise<Object>} Ingestion result with statistics
 * @throws {APIError} If the request fails
 */
export async function ingestGithub(customRepos = null) {
  const response = await fetch(`${API_BASE_URL}/api/ingest/github`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(
      customRepos && customRepos.length > 0
        ? { repos: customRepos }
        : {}
    ),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new APIError(
      `GitHub ingestion failed: ${response.status}`,
      response.status,
      errorData.detail || 'Unknown error'
    );
  }

  return response.json();
}
