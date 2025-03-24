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

// Debug logger function for API calls
const apiDebugLog = (message: string, data?: any) => {
    console.log(`[EmailAPI] ${message}`, data || '');
};

// Email-related API methods
const emailApi = {
    // Search emails with optional filters
    searchEmails: (params = {}) => {
        apiDebugLog('Searching emails with params:', params);
        return api.get('/emails/search', { params })
            .then(response => {
                apiDebugLog('Search emails response:', {
                    status: response.status,
                    emailCount: response.data.data?.length || 0,
                    metadata: response.data.meta
                });
                return response;
            })
            .catch(error => {
                apiDebugLog('Search emails error:', {
                    status: error.response?.status,
                    message: error.response?.data?.message,
                    error
                });
                throw error;
            });
    },

    // Get emails for a specific contact
    getContactEmails: (email: string) => {
        apiDebugLog('Getting emails for contact:', email);
        return api.get(`/contacts/${email}/emails`)
            .then(response => {
                apiDebugLog('Get contact emails response:', {
                    status: response.status,
                    emailCount: response.data.data?.length || 0,
                    metadata: response.data.meta
                });
                return response;
            })
            .catch(error => {
                apiDebugLog('Get contact emails error:', {
                    status: error.response?.status,
                    message: error.response?.data?.message,
                    error
                });
                throw error;
            });
    },

    // Sync emails for a specific contact
    syncContactEmails: (email: string) => {
        apiDebugLog('Syncing emails for contact:', email);
        return api.post(`/contacts/${email}/sync-emails`, {})
            .then(response => {
                apiDebugLog('Sync contact emails response:', {
                    status: response.status,
                    data: response.data
                });
                return response;
            })
            .catch(error => {
                apiDebugLog('Sync contact emails error:', {
                    status: error.response?.status,
                    message: error.response?.data?.message,
                    error
                });
                throw error;
            });
    },

    // Sync all emails
    syncAllEmails: () => {
        apiDebugLog('Syncing all emails');
        return api.post('/emails/sync', {})
            .then(response => {
                apiDebugLog('Sync all emails response:', {
                    status: response.status,
                    data: response.data
                });
                return response;
            })
            .catch(error => {
                apiDebugLog('Sync all emails error:', {
                    status: error.response?.status,
                    message: error.response?.data?.message,
                    headers: error.response?.headers,
                    config: error.config,
                    error
                });
                throw error;
            });
    }
};

export { emailApi };
export default api;