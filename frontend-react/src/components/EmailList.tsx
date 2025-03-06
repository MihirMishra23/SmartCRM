import React, { useEffect, useState } from 'react';
import {
    Box,
    Typography,
    CircularProgress,
    Alert,
    TextField,
    InputAdornment,
    List,
    ListItemButton,
    ListItemText,
    Divider,
    Paper,
    Container,
    Stack,
    Button
} from '@mui/material';
import { Search as SearchIcon, Refresh as RefreshIcon } from '@mui/icons-material';
import { emailApi } from '../services/api';
import { Email, EmailMetadata } from '../types/email';

// Debug logger function
const debugLog = (message: string, data?: any) => {
    console.log(`[EmailDebug] ${message}`, data || '');
};

const EmailList: React.FC = () => {
    const [emails, setEmails] = useState<Email[]>([]);
    const [metadata, setMetadata] = useState<EmailMetadata>({ total: 0 });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedEmail, setSelectedEmail] = useState<Email | null>(null);
    const [syncing, setSyncing] = useState(false);

    const fetchEmails = async () => {
        debugLog('Fetching emails with search term:', searchTerm);
        try {
            setLoading(true);
            setError(null);

            // Use the search endpoint with no filters to get all emails
            const response = await emailApi.searchEmails({
                limit: 50,
                offset: 0,
                q: searchTerm
            });

            debugLog('Received email response:', {
                count: response.data.data.length,
                metadata: response.data.meta
            });

            // Log each email's key information
            response.data.data.forEach((email: Email, index: number) => {
                debugLog(`Email ${index + 1}/${response.data.data.length}:`, {
                    id: email.id,
                    subject: email.subject,
                    sender: email.sender_email,
                    date: email.date,
                    read: email.read,
                    has_attachments: email.has_attachments
                });
            });

            setEmails(response.data.data);
            setMetadata(response.data.meta);
        } catch (err: any) {
            const errorMessage = err.response?.data?.message || 'Failed to fetch emails';
            debugLog('Error fetching emails:', {
                message: errorMessage,
                error: err
            });
            setError(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    const handleSyncEmails = async () => {
        debugLog('Starting email sync operation');
        try {
            setSyncing(true);
            setError(null);
            setSuccessMessage(null);

            debugLog('Sending sync request to API');
            const syncResponse = await emailApi.syncAllEmails();

            const syncData = syncResponse.data.data || {};
            const syncMeta = syncResponse.data.meta || {};

            debugLog('Sync response received:', syncResponse.data);

            // Display sync results
            const totalEmails = syncMeta.total_emails || 0;
            const savedEmails = syncMeta.saved || 0;
            const skippedEmails = syncMeta.skipped || 0;
            const failedEmails = syncMeta.failed || 0;

            // Show success message with sync details
            setSuccessMessage(`Sync completed: ${savedEmails} new emails saved, ${skippedEmails} duplicates skipped, ${failedEmails} failed.`);

            // Refresh the email list after syncing
            debugLog('Refreshing email list after sync');
            await fetchEmails();
        } catch (err: any) {
            const errorMessage = err.response?.data?.message || 'Failed to sync emails';
            debugLog('Error syncing emails:', {
                message: errorMessage,
                status: err.response?.status,
                data: err.response?.data,
                error: err
            });
            setError(errorMessage);
            setSuccessMessage(null);
        } finally {
            setSyncing(false);
            debugLog('Email sync operation completed');
        }
    };

    useEffect(() => {
        debugLog('EmailList component mounted, fetching initial emails');
        fetchEmails();

        return () => {
            debugLog('EmailList component unmounting');
        };
    }, []);

    const handleEmailSelect = (email: Email) => {
        debugLog('Email selected:', {
            id: email.id,
            subject: email.subject,
            sender: email.sender_email,
            date: email.date
        });
        setSelectedEmail(email);
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    };

    if (loading) {
        debugLog('Rendering loading state');
        return (
            <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
                <CircularProgress />
            </Box>
        );
    }

    debugLog('Rendering EmailList component with', {
        emailCount: emails.length,
        hasSelectedEmail: !!selectedEmail,
        metadata
    });

    return (
        <Container sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: 'calc(100vh - 64px)',
            py: 4,
            width: '100vw',
            maxWidth: '100%',
        }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" mb={3} sx={{ width: '100%' }}>
                <Typography variant="h5" component="h1">
                    Emails {metadata.total > 0 ? `(${metadata.total})` : ''}
                </Typography>
                <Button
                    variant="contained"
                    color="primary"
                    startIcon={<RefreshIcon />}
                    onClick={handleSyncEmails}
                    disabled={syncing}
                >
                    {syncing ? 'Syncing...' : 'Sync Emails'}
                </Button>
            </Stack>

            {error && (
                <Alert severity="error" sx={{ mb: 3, width: '100%' }}>
                    {error}
                </Alert>
            )}

            {successMessage && (
                <Alert severity="success" sx={{ mb: 3, width: '100%' }}>
                    {successMessage}
                </Alert>
            )}

            <TextField
                fullWidth
                variant="outlined"
                placeholder="Search emails..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                sx={{ mb: 3 }}
                InputProps={{
                    startAdornment: (
                        <InputAdornment position="start">
                            <SearchIcon />
                        </InputAdornment>
                    ),
                    endAdornment: (
                        <InputAdornment position="end">
                            <Button
                                variant="contained"
                                size="small"
                                onClick={fetchEmails}
                            >
                                Search
                            </Button>
                        </InputAdornment>
                    ),
                }}
            />

            <Box sx={{ display: 'flex', width: '100%', gap: 2 }}>
                {/* Email List */}
                <Paper sx={{ width: '40%', maxHeight: 'calc(100vh - 250px)', overflow: 'auto' }}>
                    {emails.length === 0 ? (
                        <Typography p={3} color="text.secondary" align="center">
                            No emails found.
                        </Typography>
                    ) : (
                        <List>
                            {emails.map((email, index) => (
                                <React.Fragment key={email.id}>
                                    <ListItemButton
                                        onClick={() => handleEmailSelect(email)}
                                        selected={selectedEmail?.id === email.id}
                                        sx={{
                                            fontWeight: !email.read ? 'bold' : 'normal',
                                            backgroundColor: selectedEmail?.id === email.id ? 'rgba(0, 0, 0, 0.04)' : 'transparent'
                                        }}
                                    >
                                        <ListItemText
                                            primary={
                                                <Typography
                                                    variant="body1"
                                                    fontWeight={!email.read ? 'bold' : 'normal'}
                                                >
                                                    {email.subject || '(No Subject)'}
                                                    <Typography component="span" variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                                                        (ID: {email.id})
                                                    </Typography>
                                                </Typography>
                                            }
                                            secondary={
                                                <>
                                                    <Typography variant="body2" component="span">
                                                        {email.sender_name || email.sender_email}
                                                    </Typography>
                                                    <Typography variant="caption" component="p" color="text.secondary">
                                                        {formatDate(email.date)}
                                                    </Typography>
                                                </>
                                            }
                                        />
                                    </ListItemButton>
                                    {index < emails.length - 1 && <Divider />}
                                </React.Fragment>
                            ))}
                        </List>
                    )}
                </Paper>

                {/* Email Detail View */}
                <Paper sx={{ width: '60%', p: 3, maxHeight: 'calc(100vh - 250px)', overflow: 'auto' }}>
                    {selectedEmail ? (
                        <>
                            <Typography variant="h6" gutterBottom>
                                {selectedEmail.subject || '(No Subject)'}
                                <Typography component="span" variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                                    (ID: {selectedEmail.id})
                                </Typography>
                            </Typography>

                            <Box sx={{ mb: 2 }}>
                                <Typography variant="body2">
                                    <strong>From:</strong> {selectedEmail.sender_name} &lt;{selectedEmail.sender_email}&gt;
                                </Typography>
                                <Typography variant="body2">
                                    <strong>To:</strong> {selectedEmail.recipient_name || ''} &lt;{selectedEmail.recipient_email}&gt;
                                </Typography>
                                <Typography variant="body2">
                                    <strong>Date:</strong> {formatDate(selectedEmail.date)}
                                </Typography>
                                <Typography variant="body2">
                                    <strong>Read:</strong> {selectedEmail.read ? 'Yes' : 'No'}
                                </Typography>
                                <Typography variant="body2">
                                    <strong>Has Attachments:</strong> {selectedEmail.has_attachments ? 'Yes' : 'No'}
                                </Typography>
                                {selectedEmail.thread_id && (
                                    <Typography variant="body2">
                                        <strong>Thread ID:</strong> {selectedEmail.thread_id}
                                    </Typography>
                                )}
                            </Box>

                            <Divider sx={{ my: 2 }} />

                            <Box sx={{ whiteSpace: 'pre-wrap' }}>
                                {selectedEmail.content}
                            </Box>
                        </>
                    ) : (
                        <Typography color="text.secondary" align="center">
                            Select an email to view its contents
                        </Typography>
                    )}
                </Paper>
            </Box>
        </Container>
    );
};

export default EmailList; 