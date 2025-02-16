# API Routes

This section documents all available API endpoints in the Inbox Manager application.

## Contact Management

### Get Contacts

```http
GET /api/contacts
```

Retrieve a paginated list of all contacts.

**Query Parameters:**
- `page` (integer, default: 1): Page number for pagination
- `per_page` (integer, default: 20): Number of items per page

**Response:**
```json
{
    "status": "success",
    "timestamp": "2024-03-20T10:00:00Z",
    "data": [
        {
            "id": "uuid",
            "name": "John Doe",
            "company": "Example Corp",
            "contact_methods": [
                {
                    "type": "email",
                    "value": "john@example.com"
                }
            ]
        }
    ],
    "meta": {
        "page": 1,
        "per_page": 20,
        "total": 100
    }
}
```

### Create Contact

```http
POST /api/contacts
```

Create a new contact.

**Request Body:**
```json
{
    "name": "John Doe",
    "company": "Example Corp",
    "contact_methods": [
        {
            "type": "email",
            "value": "john@example.com"
        }
    ]
}
```

**Response:**
```json
{
    "status": "success",
    "timestamp": "2024-03-20T10:00:00Z",
    "message": "Contact created successfully",
    "data": {
        "id": "uuid",
        "name": "John Doe",
        "company": "Example Corp",
        "contact_methods": [
            {
                "type": "email",
                "value": "john@example.com"
            }
        ]
    }
}
```

### Delete Contact

```http
DELETE /api/contacts/{email}
```

Delete a contact by their email address.

**Response:**
```json
{
    "status": "success",
    "timestamp": "2024-03-20T10:00:00Z",
    "message": "Contact deleted successfully"
}
```

## Email Management

### Get Contact Emails

```http
GET /api/contacts/{email}/emails
```

Get all emails associated with a specific contact.

**Response:**
```json
{
    "status": "success",
    "timestamp": "2024-03-20T10:00:00Z",
    "data": [
        {
            "id": "uuid",
            "subject": "Meeting Tomorrow",
            "sender": "john@example.com",
            "received_at": "2024-03-19T15:00:00Z",
            "snippet": "Let's discuss the project..."
        }
    ],
    "meta": {
        "total": 10
    }
}
```

### Sync Contact Emails

```http
POST /api/contacts/{email}/sync-emails
```

Synchronize emails for a specific contact from Gmail.

**Response:**
```json
{
    "status": "success",
    "timestamp": "2024-03-20T10:00:00Z",
    "message": "Emails synced successfully",
    "meta": {
        "email_count": 25
    }
}
```

### Sync All Emails

```http
POST /api/emails/sync
```

Synchronize emails for all contacts or filtered by search criteria.

**Request Body:**
```json
{
    "name": "John",
    "email": "john@example.com",
    "company": "Example Corp"
}
```

**Response:**
```json
{
    "status": "success",
    "timestamp": "2024-03-20T10:00:00Z",
    "message": "Emails synced successfully",
    "meta": {
        "email_count": 100,
        "contact_count": 5
    }
}
```

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
    "status": "error",
    "timestamp": "2024-03-20T10:00:00Z",
    "error": {
        "message": "Invalid request data",
        "code": 400
    }
}
```

### 404 Not Found
```json
{
    "status": "error",
    "timestamp": "2024-03-20T10:00:00Z",
    "error": {
        "message": "Resource not found",
        "code": 404
    }
}
```

### 500 Internal Server Error
```json
{
    "status": "error",
    "timestamp": "2024-03-20T10:00:00Z",
    "error": {
        "message": "An unexpected error occurred",
        "code": 500
    }
}
``` 