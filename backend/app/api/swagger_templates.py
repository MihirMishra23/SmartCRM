"""
Reusable templates for Swagger/OpenAPI documentation.
These templates define common patterns used across different API endpoints.
"""

from .swagger_schemas import (
    SwaggerProperty,
    SwaggerParameter,
    SwaggerSchema,
    SwaggerResponse,
    string_prop,
    integer_prop,
    datetime_prop,
    array_prop,
)

# Common Response Templates
SUCCESS_RESPONSE = SwaggerSchema(
    type="object",
    properties={
        "status": SwaggerProperty(type="string", enum=["success"]),
        "timestamp": SwaggerProperty(type="string", format="date-time"),
        "message": string_prop(),
        "data": SwaggerProperty(type="object"),
        "meta": SwaggerProperty(type="object"),
    },
)

ERROR_SCHEMA = SwaggerSchema(
    type="object",
    properties={
        "status": SwaggerProperty(type="string", enum=["error"]),
        "timestamp": SwaggerProperty(type="string", format="date-time"),
        "error": SwaggerSchema(
            type="object",
            properties={
                "code": integer_prop("HTTP status code"),
                "message": string_prop("Error description"),
            },
        ).to_dict(),
    },
)

# Common Error Responses
ERROR_400 = {"400": SwaggerResponse(description="Bad Request", schema=ERROR_SCHEMA)}
ERROR_404 = {"404": SwaggerResponse(description="Not Found", schema=ERROR_SCHEMA)}
ERROR_500 = {
    "500": SwaggerResponse(description="Internal Server Error", schema=ERROR_SCHEMA)
}

# Common Parameters
PAGE_PARAM = SwaggerParameter(
    name="page",
    in_="query",
    type="integer",
    description="Page number for pagination",
    default=1,
)

PER_PAGE_PARAM = SwaggerParameter(
    name="per_page",
    in_="query",
    type="integer",
    description="Number of items per page",
    default=20,
)

EMAIL_PARAM = SwaggerParameter(
    name="email",
    in_="path",
    type="string",
    description="Email address of the contact",
    required=True,
)

# Common Model Schemas
CONTACT_METHOD_SCHEMA = SwaggerSchema(
    type="object",
    properties={
        "type": SwaggerProperty(type="string", enum=["email", "phone", "linkedin"]),
        "value": string_prop("Contact method value"),
    },
)

CONTACT_SCHEMA = SwaggerSchema(
    type="object",
    properties={
        "name": string_prop("Contact's full name"),
        "company": string_prop("Company name"),
        "contact_methods": array_prop(CONTACT_METHOD_SCHEMA.to_dict()),
    },
    required=["name"],
)

EMAIL_SCHEMA = SwaggerSchema(
    type="object",
    properties={
        "id": string_prop("Email ID"),
        "subject": string_prop("Email subject"),
        "sender": string_prop("Sender's email address"),
        "received_at": datetime_prop("When the email was received"),
        "snippet": string_prop("Email preview snippet"),
    },
)


# Response Generators
def create_list_response(item_schema: SwaggerSchema) -> SwaggerResponse:
    """Create a response schema for list endpoints with pagination."""
    return SwaggerResponse(
        description="List retrieved successfully",
        schema=SwaggerSchema(
            type="object",
            properties={
                "data": array_prop(item_schema.to_dict()),
                "meta": SwaggerSchema(
                    type="object",
                    properties={
                        "total": integer_prop("Total number of items"),
                        "page": integer_prop("Current page number"),
                        "per_page": integer_prop("Items per page"),
                    },
                ).to_dict(),
            },
        ),
    )


def create_single_response(item_schema: SwaggerSchema) -> SwaggerResponse:
    """Create a response schema for single item endpoints."""
    return SwaggerResponse(
        description="Item retrieved successfully",
        schema=SwaggerSchema(
            type="object",
            properties={
                "data": item_schema.to_dict(),
                "meta": SwaggerProperty(type="object"),
            },
        ),
    )


# Endpoint documentation templates
GET_CONTACTS_TEMPLATE = {
    "summary": "Get all contacts",
    "description": "Retrieve a list of all contacts with optional filtering",
    "parameters": [PAGE_PARAM, PER_PAGE_PARAM],
    "responses": {
        "200": create_single_response(CONTACT_SCHEMA),
        **ERROR_400,
        **ERROR_404,
        **ERROR_500,
    },
}

CREATE_CONTACT_TEMPLATE = {
    "summary": "Create a new contact",
    "description": "Create a new contact with the provided information",
    "parameters": [
        {"name": "body", "in": "body", "required": True, "schema": CONTACT_SCHEMA}
    ],
    "responses": {
        "201": create_single_response(CONTACT_SCHEMA),
        **ERROR_400,
        **ERROR_500,
    },
}

GET_CONTACT_EMAILS_TEMPLATE = {
    "summary": "Get contact emails",
    "description": "Get all emails associated with a specific contact",
    "parameters": [EMAIL_PARAM],
    "responses": {
        "200": create_list_response(EMAIL_SCHEMA),
        **ERROR_400,
        **ERROR_404,
        **ERROR_500,
    },
}
