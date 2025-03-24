import { Box, Typography, Button, Snackbar } from '@mui/material';
import { useState } from 'react';
import api from '../services/api';

function Homepage() {
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [showMessage, setShowMessage] = useState(false);

    const handleTestClick = async () => {
        setLoading(true);
        try {
            const response = await api.get('/test', {
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                }
            });
            setMessage(response.data.message);
            setShowMessage(true);
        } catch (error) {
            setMessage('Failed to test connection');
            setShowMessage(true);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Box
            sx={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: 'calc(100vh - 64px)',
                textAlign: 'center',
                py: 4,
                width: '100vw',
                maxWidth: '100%',
            }}
        >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                <Typography
                    variant="h2"
                    component="h1"
                >
                    SmartCRM
                </Typography>
                <Button
                    variant="contained"
                    onClick={handleTestClick}
                    disabled={loading}
                >
                    Test API
                </Button>
            </Box>
            <Typography
                variant="body1"
                sx={{
                    maxWidth: '600px',
                    fontSize: '1.1rem',
                    lineHeight: 1.6
                }}
            >
                Welcome to the SmartCRM! Excited to have you here! Please refer to the toolbar at the top of the page for actions you can do.
            </Typography>
            <Snackbar
                open={showMessage}
                autoHideDuration={6000}
                onClose={() => setShowMessage(false)}
                message={message}
            />
        </Box>
    );
}

export default Homepage;