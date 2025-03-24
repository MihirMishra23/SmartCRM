export interface EmailRecipient {
    id: number;
    name: string;
    email: string;
}

export interface Email {
    id: number;
    subject: string;
    content: string;
    date: string;
    sender_id: number;
    sender_name: string;
    sender_email: string;
    recipient_id: number;
    recipient_name: string;
    recipient_email: string;
    recipients?: EmailRecipient[];
    thread_id: string;
    read: boolean;
    has_attachments: boolean;
}

export interface EmailMetadata {
    total: number;
    has_more?: boolean;
    limit?: number;
    offset?: number;
} 