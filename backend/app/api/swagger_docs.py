"""
Swagger/OpenAPI documentation for API endpoints.
This file contains the actual API documentation using schemas and templates.
"""

from .swagger_schemas import SwaggerTemplate
from .swagger_templates import (
    CONTACT_SCHEMA,
    EMAIL_SCHEMA,
    PAGE_PARAM,
    PER_PAGE_PARAM,
    EMAIL_PARAM,
    ERROR_400,
    ERROR_404,
    ERROR_500,
    create_list_response,
    create_single_response,
)

# Contact Endpoints
GET_CONTACTS_DOCS = SwaggerTemplate(
    summary="Get all contacts",
    description="Retrieve a list of all contacts with optional filtering",
    parameters=[PAGE_PARAM, PER_PAGE_PARAM],
    responses={
        "200": create_list_response(CONTACT_SCHEMA),
        "400": ERROR_400,
        "404": ERROR_404,
        "500": ERROR_500,
    },
).to_dict()

CREATE_CONTACT_DOCS = SwaggerTemplate(
    summary="Create a new contact",
    description="Create a new contact with the provided information",
    parameters=[
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": CONTACT_SCHEMA.to_dict(),
        }
    ],
    responses={
        "201": create_single_response(CONTACT_SCHEMA),
        "400": ERROR_400,
        "500": ERROR_500,
    },
).to_dict()

DELETE_CONTACT_DOCS = SwaggerTemplate(
    summary="Delete a contact",
    description="Delete a contact by their email address",
    parameters=[EMAIL_PARAM],
    responses={
        "200": create_single_response(CONTACT_SCHEMA),
        "404": ERROR_404,
        "500": ERROR_500,
    },
).to_dict()

# Email Endpoints
GET_CONTACT_EMAILS_DOCS = SwaggerTemplate(
    summary="Get contact emails",
    description="Get all emails associated with a specific contact",
    parameters=[EMAIL_PARAM],
    responses={
        "200": create_list_response(EMAIL_SCHEMA),
        "400": ERROR_400,
        "404": ERROR_404,
        "500": ERROR_500,
    },
).to_dict()

SYNC_CONTACT_EMAILS_DOCS = SwaggerTemplate(
    summary="Sync contact emails",
    description="Synchronize emails for a specific contact from Gmail",
    parameters=[EMAIL_PARAM],
    responses={
        "200": create_single_response(EMAIL_SCHEMA),
        "400": ERROR_400,
        "404": ERROR_404,
        "500": ERROR_500,
    },
).to_dict()

SYNC_ALL_EMAILS_DOCS = SwaggerTemplate(
    summary="Sync all emails",
    description="Synchronize emails for all contacts or filtered by search criteria",
    parameters=[
        {
            "name": "body",
            "in": "body",
            "required": False,
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Filter by contact name"},
                    "email": {
                        "type": "string",
                        "description": "Filter by email address",
                    },
                    "company": {
                        "type": "string",
                        "description": "Filter by company name",
                    },
                },
            },
        }
    ],
    responses={
        "200": create_single_response(EMAIL_SCHEMA),
        "400": ERROR_400,
        "404": ERROR_404,
        "500": ERROR_500,
    },
).to_dict()
