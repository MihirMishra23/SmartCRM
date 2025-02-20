export interface ContactMethod {
    type: 'email' | 'phone' | 'linkedin';
    value: string;
    is_primary?: boolean;
}

export interface Contact {
    id: number;
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