import axios from "axios";

// Read our target endpoint URL from environment variables, fallback to local host port 8000
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Centralized, type-safe Axios instance configured specifically 
 * for the IndustryOS enterprise network perimeter.
 */
export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 10000, // Hard stop request after 10 seconds to prevent thread stalling
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
  withCredentials: true, // Forces browser to pass secure authentication cookie signatures
});

// Optional: Global response interceptor to handle enterprise logging
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("🚨 NETWORK TRANSPORT EXCEPTION INTERCEPTED:", {
      status: error.response?.status,
      code: error.response?.data?.error_code,
      message: error.response?.data?.message || error.message,
    });
    return Promise.reject(error);
  }
);