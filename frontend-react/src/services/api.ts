import axios from 'axios';

// Create axios instance with default config
const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:5000',
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add response interceptor for error handling
api.interceptors.response.use(
    (response) => response,
    (error) => {
        // Handle specific error cases
        if (error.response) {
            // Server responded with error status
            console.error('API Error:', error.response.data);
        } else if (error.request) {
            // Request was made but no response received
            console.error('Network Error:', error.request);
        } else {
            // Something else happened
            console.error('Error:', error.message);
        }
        return Promise.reject(error);
    }
);

export default api; 