import { Box, Typography } from '@mui/material';

function Homepage() {
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
            <Typography
                variant="h2"
                component="h1"
                gutterBottom
            >
                SmartCRM
            </Typography>
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
        </Box>
    );
}

export default Homepage;