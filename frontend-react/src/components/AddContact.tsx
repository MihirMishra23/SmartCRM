import React, { useState } from 'react';
import {
    Box,
    Button,
    TextField,
    Typography,
    Paper,
    Alert,
    IconButton,
    Stack,
    MenuItem,
    CircularProgress,
    FormControlLabel,
    Switch,
    Checkbox
} from '@mui/material';
import { Add as AddIcon, Delete as DeleteIcon } from '@mui/icons-material';
import api from '../services/api';

interface ContactMethod {
    type: 'email' | 'phone' | 'linkedin';
    value: string;
    is_primary?: boolean;
}

interface ContactFormData {
    name: string;
    company?: string;
    position?: string;
    last_contacted?: string;
    follow_up_date?: string;
    warm?: boolean;
    reminder?: boolean;
    notes?: string;
    contact_methods: ContactMethod[];
}

const CONTACT_METHOD_TYPES = [
    { value: 'email', label: 'Email' },
    { value: 'phone', label: 'Phone' },
    { value: 'linkedin', label: 'LinkedIn' }
];

const AddContact: React.FC = () => {
    const [formData, setFormData] = useState<ContactFormData>({
        name: '',
        company: '',
        position: '',
        last_contacted: '',
        follow_up_date: '',
        warm: false,
        reminder: true,
        notes: '',
        contact_methods: [{ type: 'email', value: '', is_primary: true }]
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    const handleInputChange = (field: string) => (event: React.ChangeEvent<HTMLInputElement>) => {
        setFormData(prev => ({
            ...prev,
            [field]: event.target.value
        }));
        setError(null);
        setSuccess(false);
    };

    const handleContactMethodChange = (index: number, field: 'type' | 'value') => (
        event: React.ChangeEvent<HTMLInputElement>
    ) => {
        const newContactMethods = [...formData.contact_methods];
        newContactMethods[index] = {
            ...newContactMethods[index],
            [field]: event.target.value
        };
        setFormData(prev => ({
            ...prev,
            contact_methods: newContactMethods
        }));
        setError(null);
        setSuccess(false);
    };

    const addContactMethod = () => {
        setFormData(prev => ({
            ...prev,
            contact_methods: [...prev.contact_methods, { type: 'email', value: '', is_primary: false }]
        }));
    };

    const removeContactMethod = (index: number) => {
        if (formData.contact_methods.length > 1) {
            setFormData(prev => ({
                ...prev,
                contact_methods: prev.contact_methods.filter((_, i) => i !== index)
            }));
        }
    };

    const validateForm = (): boolean => {
        if (!formData.name.trim()) {
            setError('Name is required');
            return false;
        }

        if (!formData.contact_methods.length) {
            setError('At least one contact method is required');
            return false;
        }

        for (const method of formData.contact_methods) {
            if (!method.value.trim()) {
                setError('All contact method values must be filled');
                return false;
            }

            if (method.type === 'email' && !method.value.includes('@')) {
                setError('Invalid email format');
                return false;
            }
        }

        return true;
    };

    const handleSubmit = async (event: React.FormEvent) => {
        event.preventDefault();

        if (!validateForm()) {
            return;
        }

        try {
            setLoading(true);
            setError(null);

            console.log('Form Data Type:', typeof formData);
            console.log('Form Data Structure:', {
                raw: formData,
                stringified: JSON.stringify(formData),
                parsed: JSON.parse(JSON.stringify(formData))
            });
            console.log('Contact Methods:', formData.contact_methods);

            const response = await api.post('/contacts', JSON.parse(JSON.stringify(formData)));
            console.log('API Response:', response);

            setSuccess(true);
            setFormData({
                name: '',
                company: '',
                position: '',
                last_contacted: '',
                follow_up_date: '',
                warm: false,
                reminder: true,
                notes: '',
                contact_methods: [{ type: 'email', value: '', is_primary: true }]
            });
        } catch (err: any) {
            console.error('API Error:', {
                error: err,
                response: err.response,
                data: err.response?.data,
                status: err.response?.status
            });
            setError(err.response?.data?.message || 'Failed to create contact');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Paper elevation={3} sx={{ p: 4, maxWidth: 600, mx: 'auto' }}>
            <form onSubmit={handleSubmit}>
                <Stack spacing={3}>
                    <Typography variant="h5" component="h2" gutterBottom>
                        Add New Contact
                    </Typography>

                    {error && (
                        <Alert severity="error">
                            {error}
                        </Alert>
                    )}

                    {success && (
                        <Alert severity="success">
                            Contact created successfully!
                        </Alert>
                    )}

                    <TextField
                        label="Name"
                        value={formData.name}
                        onChange={handleInputChange('name')}
                        required
                        fullWidth
                    />

                    <TextField
                        label="Company"
                        value={formData.company}
                        onChange={handleInputChange('company')}
                        fullWidth
                    />

                    <TextField
                        label="Position"
                        value={formData.position}
                        onChange={handleInputChange('position')}
                        fullWidth
                    />

                    <TextField
                        label="Last Contacted"
                        type="date"
                        value={formData.last_contacted}
                        onChange={handleInputChange('last_contacted')}
                        fullWidth
                        InputLabelProps={{ shrink: true }}
                    />

                    <TextField
                        label="Follow-up Date"
                        type="date"
                        value={formData.follow_up_date}
                        onChange={handleInputChange('follow_up_date')}
                        fullWidth
                        InputLabelProps={{ shrink: true }}
                    />

                    <Box display="flex" gap={2}>
                        <FormControlLabel
                            control={
                                <Switch
                                    checked={formData.warm}
                                    onChange={(e) =>
                                        setFormData(prev => ({
                                            ...prev,
                                            warm: e.target.checked
                                        }))
                                    }
                                />
                            }
                            label="Warm Contact"
                        />

                        <FormControlLabel
                            control={
                                <Switch
                                    checked={formData.reminder}
                                    onChange={(e) =>
                                        setFormData(prev => ({
                                            ...prev,
                                            reminder: e.target.checked
                                        }))
                                    }
                                />
                            }
                            label="Set Reminder"
                        />
                    </Box>

                    <TextField
                        label="Notes"
                        value={formData.notes}
                        onChange={handleInputChange('notes')}
                        fullWidth
                        multiline
                        rows={4}
                    />

                    <Box>
                        <Typography variant="subtitle1" gutterBottom>
                            Contact Methods
                        </Typography>

                        <Stack spacing={2}>
                            {formData.contact_methods.map((method, index) => (
                                <Box key={index} display="flex" gap={2} alignItems="center">
                                    <TextField
                                        select
                                        label="Type"
                                        value={method.type}
                                        onChange={handleContactMethodChange(index, 'type')}
                                        sx={{ width: '150px' }}
                                    >
                                        {CONTACT_METHOD_TYPES.map(option => (
                                            <MenuItem key={option.value} value={option.value}>
                                                {option.label}
                                            </MenuItem>
                                        ))}
                                    </TextField>

                                    <TextField
                                        label="Value"
                                        value={method.value}
                                        onChange={handleContactMethodChange(index, 'value')}
                                        required
                                        fullWidth
                                        type={method.type === 'email' ? 'email' : 'text'}
                                    />

                                    <FormControlLabel
                                        control={
                                            <Checkbox
                                                checked={method.is_primary}
                                                onChange={(e) => {
                                                    const newMethods = [...formData.contact_methods];
                                                    // Uncheck other primary methods of the same type
                                                    if (e.target.checked) {
                                                        newMethods.forEach((m, i) => {
                                                            if (i !== index && m.type === method.type) {
                                                                m.is_primary = false;
                                                            }
                                                        });
                                                    }
                                                    newMethods[index] = {
                                                        ...method,
                                                        is_primary: e.target.checked
                                                    };
                                                    setFormData(prev => ({
                                                        ...prev,
                                                        contact_methods: newMethods
                                                    }));
                                                }}
                                            />
                                        }
                                        label="Primary"
                                    />

                                    <IconButton
                                        onClick={() => removeContactMethod(index)}
                                        disabled={formData.contact_methods.length === 1}
                                        color="error"
                                    >
                                        <DeleteIcon />
                                    </IconButton>
                                </Box>
                            ))}
                        </Stack>

                        <Button
                            startIcon={<AddIcon />}
                            onClick={addContactMethod}
                            sx={{ mt: 2 }}
                        >
                            Add Contact Method
                        </Button>
                    </Box>

                    <Button
                        type="submit"
                        variant="contained"
                        color="primary"
                        disabled={loading}
                        sx={{ mt: 2 }}
                    >
                        {loading ? <CircularProgress size={24} /> : 'Create Contact'}
                    </Button>
                </Stack>
            </form>
        </Paper>
    );
};

export default AddContact; 