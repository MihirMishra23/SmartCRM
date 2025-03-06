export interface Email {
    id: number;
    subject: string;
    content: string;
    date: string;
    sender_id: number;
    sender_name: string;
    sender_email: string;
    recipient_id?: number;
    recipient_name?: string;
    recipient_email: string;
    thread_id?: string;
    read: boolean;
    has_attachments: boolean;
}

export interface EmailMetadata {
    total: number;
    sent_count?: number;
    received_count?: number;
    has_more?: boolean;
    limit?: number;
    offset?: number;
} 