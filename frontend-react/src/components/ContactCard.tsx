import React from 'react';
import {
    Card,
    CardContent,
    Typography,
    Chip,
    Box,
    IconButton,
    Tooltip,
    Stack,
    Divider
} from '@mui/material';
import {
    Email as EmailIcon,
    Phone as PhoneIcon,
    LinkedIn as LinkedInIcon,
    Edit as EditIcon,
    Delete as DeleteIcon,
    Star as StarIcon
} from '@mui/icons-material';
import { Contact } from '../types/contact';

interface ContactMethod {
    type: 'email' | 'phone' | 'linkedin';
    value: string;
    is_primary?: boolean;
}

interface ContactCardProps {
    contact: Contact;
    onEdit?: (contact: Contact) => void;
    onDelete?: (contact: Contact) => void;
}

const getMethodIcon = (type: string) => {
    switch (type) {
        case 'email':
            return <EmailIcon fontSize="small" />;
        case 'phone':
            return <PhoneIcon fontSize="small" />;
        case 'linkedin':
            return <LinkedInIcon fontSize="small" />;
        default:
            return null;
    }
};

const formatDate = (dateString?: string) => {
    if (!dateString) return '';
    return new Date(dateString).toLocaleDateString();
};

const ContactCard: React.FC<ContactCardProps> = ({ contact, onEdit, onDelete }) => {
    return (
        <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="flex-start">
                    <Box>
                        <Typography variant="h6" component="div" gutterBottom>
                            {contact.name}
                            {contact.warm && (
                                <Tooltip title="Warm Contact">
                                    <StarIcon
                                        sx={{
                                            ml: 1,
                                            color: 'warning.main',
                                            verticalAlign: 'text-bottom'
                                        }}
                                    />
                                </Tooltip>
                            )}
                        </Typography>
                        {contact.position && (
                            <Typography color="text.secondary" gutterBottom>
                                {contact.position}
                            </Typography>
                        )}
                        {contact.company && (
                            <Typography color="text.secondary" gutterBottom>
                                {contact.company}
                            </Typography>
                        )}
                    </Box>
                    <Box>
                        <IconButton size="small" onClick={() => onEdit?.(contact)}>
                            <EditIcon />
                        </IconButton>
                        <IconButton size="small" onClick={() => onDelete?.(contact)}>
                            <DeleteIcon />
                        </IconButton>
                    </Box>
                </Box>

                <Divider sx={{ my: 1.5 }} />

                <Stack spacing={1}>
                    {contact.contact_methods.map((method, index) => (
                        <Box
                            key={index}
                            display="flex"
                            alignItems="center"
                            gap={1}
                        >
                            {getMethodIcon(method.type)}
                            <Typography variant="body2">
                                {method.value}
                                {method.is_primary && (
                                    <Chip
                                        label="Primary"
                                        size="small"
                                        sx={{ ml: 1 }}
                                    />
                                )}
                            </Typography>
                        </Box>
                    ))}
                </Stack>

                {(contact.last_contacted || contact.follow_up_date) && (
                    <>
                        <Divider sx={{ my: 1.5 }} />
                        <Stack spacing={0.5}>
                            {contact.last_contacted && (
                                <Typography variant="body2" color="text.secondary">
                                    Last Contacted: {formatDate(contact.last_contacted)}
                                </Typography>
                            )}
                            {contact.follow_up_date && (
                                <Typography
                                    variant="body2"
                                    color={contact.reminder ? 'primary' : 'text.secondary'}
                                >
                                    Follow-up: {formatDate(contact.follow_up_date)}
                                </Typography>
                            )}
                        </Stack>
                    </>
                )}

                {contact.notes && (
                    <>
                        <Divider sx={{ my: 1.5 }} />
                        <Typography variant="body2" color="text.secondary">
                            {contact.notes}
                        </Typography>
                    </>
                )}
            </CardContent>
        </Card>
    );
};

export default ContactCard; 