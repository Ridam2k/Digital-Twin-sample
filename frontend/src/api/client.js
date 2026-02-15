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
 * @returns {Promise<Object>} Response object with {response, citations, mode, router_scores, out_of_scope}
 * @throws {APIError} If the request fails
 */
export async function sendQuery(queryText) {
  const response = await fetch(`${API_BASE_URL}/api/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query: queryText }),
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
