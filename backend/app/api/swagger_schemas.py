"""
Swagger schema definitions using dataclasses and TypedDict.

Note on type checking:
This module uses TypedDict for better type safety, but there are some limitations
with Python's type system when dealing with OpenAPI/Swagger schemas:

1. Dictionary key access with variable types
2. TypedDict with reserved keywords (like 'in')
3. Complex nested schema types

We use type ignores in specific places where mypy's type checking is too strict
for our valid runtime behavior.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Union, TypedDict


class PropertyDict(TypedDict, total=False):
    type: str
    description: Optional[str]
    format: Optional[str]
    enum: Optional[List[str]]
    default: Optional[Any]
    schema: Optional[Dict[str, Any]]


@dataclass
class SwaggerProperty:
    type: str
    description: Optional[str] = None
    format: Optional[str] = None
    enum: Optional[List[str]] = None
    default: Optional[Any] = None
    required: bool = False
    schema: Optional[Dict[str, Any]] = None

    def to_dict(self) -> PropertyDict:
        result: PropertyDict = {"type": self.type}
        if self.description:
            result["description"] = self.description
        if self.format:
            result["format"] = self.format
        if self.enum:
            result["enum"] = self.enum
        if self.default is not None:
            result["default"] = self.default
        if self.schema is not None:
            result["schema"] = self.schema  # type: ignore
        return result


class ParameterDict(TypedDict, total=False):
    name: str
    in_: str  # Using in_ to avoid Python keyword
    type: str
    description: str
    required: bool
    default: Any
    schema: Dict[str, Any]
    format: Optional[str]


@dataclass
class SwaggerParameter:
    name: str
    in_: str
    type: str
    description: str
    required: bool = False
    default: Optional[Any] = None
    schema: Optional[Dict[str, Any]] = None
    format: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:  # Changed return type to be more permissive
        result = {
            "name": self.name,
            "in": self.in_,  # Maps in_ to 'in' in the output
            "type": self.type,
            "description": self.description,
            "required": self.required,
        }
        if self.schema:
            result["schema"] = self.schema
        if self.default is not None:
            result["default"] = self.default
        if self.format is not None:
            result["format"] = self.format
        return result


@dataclass
class SwaggerSchema:
    type: str
    properties: Dict[str, Union[SwaggerProperty, Dict[str, Any]]]
    required: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "properties": {
                name: prop.to_dict() if isinstance(prop, SwaggerProperty) else prop
                for name, prop in self.properties.items()
            },
            "required": self.required,
        }


@dataclass
class SwaggerResponse:
    description: str
    schema: Optional[SwaggerSchema] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {"description": self.description}
        if self.schema:
            result["schema"] = self.schema.to_dict()  # type: ignore
        return result


@dataclass
class SwaggerTemplate:
    summary: str
    description: str
    parameters: List[SwaggerParameter]
    responses: Dict[str, SwaggerResponse]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "description": self.description,
            "parameters": [param.to_dict() for param in self.parameters],
            "responses": {
                code: response.to_dict() for code, response in self.responses.items()
            },
        }


# Common Properties
string_prop = lambda desc=None: SwaggerProperty(type="string", description=desc)
integer_prop = lambda desc=None: SwaggerProperty(type="integer", description=desc)
datetime_prop = lambda desc=None: SwaggerProperty(
    type="string", format="date-time", description=desc
)
array_prop = lambda items_schema: SwaggerProperty(
    type="array", schema={"items": items_schema}
)

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

# Common Schemas
CONTACT_METHOD_SCHEMA = SwaggerSchema(
    type="object",
    properties={
        "type": SwaggerProperty(type="string", enum=["email", "phone", "linkedin"]),
        "value": string_prop(),
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

# Error Responses
ERROR_400 = SwaggerResponse(
    description="Bad Request",
    schema=SwaggerSchema(
        type="object",
        properties={
            "status": SwaggerProperty(type="string", enum=["error"]),
            "error": SwaggerSchema(
                type="object",
                properties={"code": integer_prop(), "message": string_prop()},
            ).to_dict(),
        },
    ),
)

ERROR_404 = SwaggerResponse(
    description="Not Found",
    schema=SwaggerSchema(
        type="object",
        properties={
            "status": SwaggerProperty(type="string", enum=["error"]),
            "error": SwaggerSchema(
                type="object",
                properties={"code": integer_prop(), "message": string_prop()},
            ).to_dict(),
        },
    ),
)


# Template Generators
def create_list_response(item_schema: SwaggerSchema) -> SwaggerResponse:
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


# API Templates
GET_CONTACTS_TEMPLATE = SwaggerTemplate(
    summary="Get all contacts",
    description="Retrieve a list of all contacts with optional filtering",
    parameters=[PAGE_PARAM, PER_PAGE_PARAM],
    responses={
        "200": create_list_response(CONTACT_SCHEMA),
        "400": ERROR_400,
        "404": ERROR_404,
    },
).to_dict()

CREATE_CONTACT_TEMPLATE = SwaggerTemplate(
    summary="Create a new contact",
    description="Create a new contact with the provided information",
    parameters=[
        SwaggerParameter(
            name="body",
            in_="body",
            type="object",
            description="Contact information",
            required=True,
            schema=CONTACT_SCHEMA.to_dict(),
        )
    ],
    responses={
        "201": SwaggerResponse(
            description="Contact created successfully", schema=CONTACT_SCHEMA
        ),
        "400": ERROR_400,
        "409": SwaggerResponse(description="Contact already exists"),
    },
).to_dict()

GET_CONTACT_EMAILS_TEMPLATE = SwaggerTemplate(
    summary="Get contact emails",
    description="Get all emails associated with a specific contact",
    parameters=[EMAIL_PARAM],
    responses={
        "200": create_list_response(EMAIL_SCHEMA),
        "400": ERROR_400,
        "404": ERROR_404,
    },
).to_dict()
