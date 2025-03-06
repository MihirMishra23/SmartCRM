import axios from 'axios';

// Create axios instance with default config
const api = axios.create({
    baseURL: 'http://localhost:5001/api',
    headers: {
        'Content-Type': 'application/json'
    }
});

// Add request interceptor for logging
api.interceptors.request.use(
    (config) => {
        console.log('Making request:', {
            url: config.url,
            method: config.method,
            data: config.data,
            headers: config.headers
        });
        return config;
    },
    (error) => {
        console.error('Request error:', error);
        return Promise.reject(error);
    }
);

// Add response interceptor for error handling
api.interceptors.response.use(
    (response) => response,
    (error) => {
        // Handle specific error cases
        if (error.response) {
            // Server responded with error status
            console.error('API Error Details:', {
                status: error.response.status,
                statusText: error.response.statusText,
                data: error.response.data,
                headers: error.response.headers,
                config: {
                    url: error.response.config.url,
                    method: error.response.config.method,
                    data: error.response.config.data
                }
            });
        } else if (error.request) {
            // Request was made but no response received
            console.error('Network Error:', {
                request: error.request,
                config: error.config
            });
        } else {
            // Something else happened
            console.error('Error:', error.message);
        }
        return Promise.reject(error);
    }
);

// Email-related API methods
const emailApi = {
    // Search emails with optional filters
    searchEmails: (params = {}) => {
        return api.get('/emails/search', { params });
    },

    // Get emails for a specific contact
    getContactEmails: (email: string) => {
        return api.get(`/contacts/${email}/emails`);
    },

    // Sync emails for a specific contact
    syncContactEmails: (email: string) => {
        return api.post(`/contacts/${email}/sync-emails`, {});
    },

    // Sync all emails
    syncAllEmails: () => {
        return api.post('/emails/sync', {});
    }
};

export { emailApi };
export default api;