# SmartCRM

A Flask-based application for managing professional contacts and email communications.

## Project Structure

```
SmartCRM/
│── backend/                 # Backend Flask application
│   ├── app/                # Application package
│   │   ├── models/        # Database models
│   │   ├── services/      # Business logic
│   │   ├── api/           # API routes
│   │   ├── utils/         # Utility functions
│   ├── tests/             # Test files
│   ├── main.py            # Application entry point
│
│── frontend/              # Frontend application (future)
```

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables in `.env`:
   ```
   DATABASE_URL=postgresql://localhost/inbox_manager
   OPENAI_API_KEY=your_key_here
   APIFY_API_KEY=your_key_here
   ```

4. Set up Gmail API credentials:
   - Place your `gmail_credentials.json` in the root directory
   - On first run, you'll be prompted to authenticate with Gmail

5. Initialize the database:
   ```bash
   flask db init
   flask db migrate
   flask db upgrade
   ```

6. Run the application:
   ```bash
   python backend/main.py
   ```

## API Endpoints

- `GET /api/contacts` - Get all contacts
- `POST /api/contacts` - Create a new contact
- `DELETE /api/contacts/<id>` - Delete a contact
- `GET /api/emails` - Get emails for contacts
- `POST /api/sync-emails` - Sync emails from Gmail

## Development

- Run tests: `python -m pytest backend/tests/`
- Format code: `black backend/`
- Lint code: `flake8 backend/`