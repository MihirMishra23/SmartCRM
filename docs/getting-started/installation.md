# Installation Guide

This guide will help you set up Inbox Manager on your local machine.

## Prerequisites

- Python 3.8 or higher
- PostgreSQL database
- Gmail account with API access
- OpenAI API key (for contact enrichment)
- Apify API key (for web scraping)

## Step-by-Step Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/inbox-manager.git
   cd inbox-manager
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file in the root directory with:
   ```
   DATABASE_URL=postgresql://localhost/inbox_manager
   OPENAI_API_KEY=your_key_here
   APIFY_API_KEY=your_key_here
   ```

5. Set up Gmail API:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project
   - Enable Gmail API
   - Create OAuth 2.0 credentials
   - Download credentials and save as `gmail_credentials.json` in root directory

6. Initialize the database:
   ```bash
   flask db init
   flask db migrate
   flask db upgrade
   ```

## Running the Application

1. Start the development server:
   ```bash
   python backend/main.py
   ```

2. The API will be available at `http://localhost:5000`

## Troubleshooting

### Common Issues

1. Database Connection Errors
   - Verify PostgreSQL is running
   - Check DATABASE_URL in .env
   - Ensure database exists

2. Gmail Authentication Issues
   - Verify credentials file location
   - Check if OAuth consent screen is configured
   - Ensure required scopes are enabled

3. Package Installation Issues
   - Try upgrading pip: `pip install --upgrade pip`
   - Install system dependencies if needed 