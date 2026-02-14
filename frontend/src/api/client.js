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
