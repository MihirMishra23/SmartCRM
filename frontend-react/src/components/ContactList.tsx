import React, { useEffect, useState } from 'react';
import {
    Grid,
    Typography,
    Box,
    CircularProgress,
    Alert,
    TextField,
    InputAdornment,
    Button,
    Stack,
    Container
} from '@mui/material';
import { Search as SearchIcon, Add as AddIcon } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import ContactCard from './ContactCard';
import api from '../services/api';
import { Contact } from '../types/contact';

const ContactList: React.FC = () => {
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState('');
    const navigate = useNavigate();

    const fetchContacts = async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await api.get('/contacts');
            setContacts(response.data.data);
        } catch (err: any) {
            setError(err.response?.data?.message || 'Failed to fetch contacts');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchContacts();
    }, []);

    const handleEdit = (contact: Contact) => {
        // TODO: Implement edit functionality
        console.log('Edit contact:', contact);
    };

    const handleDelete = async (contact: Contact) => {
        if (!window.confirm('Are you sure you want to delete this contact?')) {
            return;
        }

        try {
            await api.delete(`/contacts/${contact.id}`);
            setContacts(contacts.filter(c => c.id !== contact.id));
        } catch (err: any) {
            setError(err.response?.data?.message || 'Failed to delete contact');
        }
    };

    const filteredContacts = contacts.filter(contact => {
        const searchLower = searchTerm.toLowerCase();
        return (
            contact.name.toLowerCase().includes(searchLower) ||
            contact.company?.toLowerCase().includes(searchLower) ||
            contact.position?.toLowerCase().includes(searchLower) ||
            contact.contact_methods.some(method =>
                method.value.toLowerCase().includes(searchLower)
            )
        );
    });

    if (loading) {
        return (
            <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
                <CircularProgress />
            </Box>
        );
    }

    return (
        <Container sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: 'calc(100vh - 64px)',
            textAlign: 'center',
            py: 4,
            width: '100vw',
            maxWidth: '100%',
        }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" mb={3} sx={{ width: '100%' }}>
                <Typography variant="h5" component="h1">
                    Contacts
                </Typography>
                <Button
                    variant="contained"
                    color="primary"
                    startIcon={<AddIcon />}
                    onClick={() => navigate('/add-contact')}
                >
                    Add Contact
                </Button>
            </Stack>

            {error && (
                <Alert severity="error" sx={{ mb: 3 }}>
                    {error}
                </Alert>
            )}

            <TextField
                fullWidth
                variant="outlined"
                placeholder="Search contacts..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                sx={{ mb: 3 }}
                InputProps={{
                    startAdornment: (
                        <InputAdornment position="start">
                            <SearchIcon />
                        </InputAdornment>
                    ),
                }}
            />

            {filteredContacts.length === 0 ? (
                <Typography color="text.secondary" align="center">
                    {contacts.length === 0
                        ? "No contacts found. Add your first contact!"
                        : "No contacts match your search."}
                </Typography>
            ) : (
                <Grid container spacing={3}>
                    {filteredContacts.map(contact => (
                        <Grid item xs={12} sm={6} md={4} key={contact.id}>
                            <ContactCard
                                contact={contact}
                                onEdit={handleEdit}
                                onDelete={handleDelete}
                            />
                        </Grid>
                    ))}
                </Grid>
            )}
        </Container>
    );
};

export default ContactList; 