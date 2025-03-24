# Contributing Guide

Thank you for considering contributing to SmartCRM! This document provides guidelines and instructions for contributing to the project.

## Getting Started

1. **Fork the Repository**
   - Click the "Fork" button on GitHub
   - Clone your fork locally:
     ```bash
     git clone https://github.com/yourusername/SmartCRM.git
     cd SmartCRM
     ```

2. **Set Up Development Environment**
   - Create virtual environment:
     ```bash
     python -m venv venv
     source venv/bin/activate  # On Windows: venv\Scripts\activate
     ```
   - Install dependencies:
     ```bash
     pip install -r requirements.txt
     ```
   - Set up pre-commit hooks:
     ```bash
     pre-commit install
     ```

## Development Workflow

1. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Write code following style guide
   - Add tests for new functionality
   - Update documentation

3. **Run Tests**
   ```bash
   python -m pytest
   ```

4. **Format and Lint Code**
   ```bash
   # Format code
   black backend/

   # Run linter
   flake8 backend/
   ```

5. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

   Follow conventional commits:
   - `feat:` New feature
   - `fix:` Bug fix
   - `docs:` Documentation
   - `test:` Tests
   - `refactor:` Code refactoring
   - `style:` Code style changes
   - `chore:` Maintenance tasks

6. **Create Pull Request**
   - Push changes to your fork
   - Create PR on GitHub
   - Fill out PR template
   - Request review

## Code Style Guide

### Python

1. **Formatting**
   - Use Black for code formatting
   - 88 characters line length
   - Use double quotes for strings

2. **Imports**
   ```python
   # Standard library
   import os
   from datetime import datetime

   # Third-party packages
   import flask
   import sqlalchemy

   # Local modules
   from app.models import Contact
   from app.services import EmailService
   ```

3. **Documentation**
   ```python
   def process_contact(contact_data: dict) -> Contact:
       """Process contact data and create a new contact.

       Args:
           contact_data: Dictionary containing contact information
               - name: Contact's full name
               - email: Contact's email address
               - company: Company name (optional)

       Returns:
           Contact: Created contact instance

       Raises:
           ValueError: If required fields are missing
       """
       pass
   ```

4. **Type Hints**
   ```python
   from typing import List, Optional, Dict

   def get_contacts(
       name: Optional[str] = None,
       company: Optional[str] = None
   ) -> List[Contact]:
       pass
   ```

### API Design

1. **URL Structure**
   - Use plural nouns for resources
   - Nest related resources
   - Use kebab-case for URLs
   ```
   GET /api/contacts
   POST /api/contacts
   GET /api/contacts/{id}/emails
   ```

2. **Response Format**
   ```json
   {
     "status": "success",
     "data": {},
     "meta": {},
     "message": "Optional message"
   }
   ```

3. **Error Handling**
   ```json
   {
     "status": "error",
     "error": {
       "code": 400,
       "message": "Error description"
     }
   }
   ```

## Testing Guidelines

1. **Test Structure**
   ```python
   def test_feature_scenario_expected():
       """Test description of what's being tested."""
       # Setup
       data = {"key": "value"}

       # Execute
       result = function_under_test(data)

       # Assert
       assert result.key == "value"
   ```

2. **Test Coverage**
   - Minimum 80% coverage
   - Test happy path and edge cases
   - Mock external services

## Documentation

1. **Code Comments**
   - Explain complex logic
   - Document assumptions
   - Note potential issues

2. **Documentation Updates**
   - Update README.md
   - Update API documentation
   - Add migration notes

## Review Process

1. **Before Submitting**
   - [ ] Tests passing
   - [ ] Code formatted
   - [ ] Documentation updated
   - [ ] Changelog updated

2. **Review Criteria**
   - Code quality and style
   - Test coverage
   - Documentation
   - Performance impact

3. **Merge Requirements**
   - Approved by maintainer
   - CI checks passing
   - No merge conflicts

## Release Process

1. **Version Numbering**
   - Follow semantic versioning
   - Update version in setup.py
   - Tag release in git

2. **Changelog**
   - Group changes by type
   - Link to PR numbers
   - Credit contributors

3. **Release Notes**
   - Summarize changes
   - Note breaking changes
   - Include upgrade guide

## Getting Help

- Create an issue for bugs
- Discuss features in discussions
- Join community chat
- Contact maintainers

## Code of Conduct

1. **Be Respectful**
   - Inclusive environment
   - Professional communication
   - Constructive feedback

2. **Contribute Positively**
   - Help others learn
   - Share knowledge
   - Improve the project

3. **Report Issues**
   - Security vulnerabilities
   - Code of conduct violations
   - Bugs and problems 