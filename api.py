from flask import Flask, request, jsonify, g
from postgres_utils import DataBase
from typing import List, Dict, Any, Optional
import traceback

app = Flask(__name__)


def get_db(test_suffix: Optional[str] = None):
    """Get database connection for the current request"""
    if "db" not in g:
        g.db = DataBase("postgres", test_suffix)
    return g.db


@app.teardown_appcontext
def close_db(error):
    """Close database connection when request ends"""
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.route("/health", methods=["GET"])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy"}), 200


@app.route("/contacts", methods=["GET"])
def get_contacts():
    """Get all contacts"""
    try:
        test_suffix = request.args.get("test_suffix")
        db = get_db(test_suffix)
        contacts = db.fetch_contacts_as_dicts()
        return jsonify(contacts), 200
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/contacts", methods=["POST"])
def add_contact():
    """
    Add a new contact
    
    Request Body:
        name: Name of the contact (required)
        contact_methods: List of contact methods (required)
            Each method must have:
            - type: Type of contact method (email, phone, linkedin, etc.)
            - value: Value of the contact method
            - is_primary: Whether this is the primary contact method
        company: Company name (optional)
        last_contacted: Date of last contact (optional)
        follow_up_date: Date to follow up (optional)
        warm: Whether this is a warm contact (optional, default: false)
        reminder: Whether to set reminders (optional, default: true)
        notes: Additional notes (optional)
        position: Job position (optional)
        
    Query Parameters:
        test_suffix: Optional test suffix for test database tables
        
    Returns:
        201: Contact added successfully
        400: Invalid request (malformed JSON, missing fields, invalid data structure, or duplicate contact information)
        500: Server error
    """
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
            
        try:
            data = request.get_json()
        except Exception as e:
            return jsonify({"error": "Invalid JSON format"}), 400
            
        if not isinstance(data, dict):
            return jsonify({"error": "Request body must be a JSON object"}), 400
        
        required_fields = ["name", "contact_methods"]

        # Validate required fields
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Validate name is a string
        if not isinstance(data["name"], str) or not data["name"].strip():
            return jsonify({"error": "Name must be a non-empty string"}), 400

        # Validate contact_methods is a list
        if not isinstance(data["contact_methods"], list):
            return jsonify({"error": "contact_methods must be an array"}), 400

        # Validate contact_methods is not empty
        if not data["contact_methods"]:
            return jsonify({"error": "At least one contact method is required"}), 400

        # Validate each contact method
        for i, method in enumerate(data["contact_methods"]):
            if not isinstance(method, dict):
                return jsonify({"error": f"Contact method at index {i} must be an object"}), 400
            
            # Check required fields in contact method
            for field in ["type", "value"]:
                if field not in method:
                    return jsonify({"error": f"Contact method at index {i} missing required field: {field}"}), 400
                if not isinstance(method[field], str) or not method[field].strip():
                    return jsonify({"error": f"Contact method at index {i} field '{field}' must be a non-empty string"}), 400

            # Validate is_primary is a boolean if present
            if "is_primary" in method and not isinstance(method["is_primary"], bool):
                return jsonify({"error": f"Contact method at index {i} field 'is_primary' must be a boolean"}), 400

        # Add contact using database utility
        test_suffix = request.args.get("test_suffix")
        db = get_db(test_suffix)
        try:
            db.add_contact(
                name=data["name"],
                contact_methods=data["contact_methods"],
                company=data.get("company"),
                last_contacted=data.get("last_contacted"),
                follow_up_date=data.get("follow_up_date"),
                warm=data.get("warm", False),
                reminder=data.get("reminder", True),
                notes=data.get("notes"),
                position=data.get("position"),
            )
            return jsonify({"message": "Contact added successfully"}), 201
        except ValueError as e:
            if "already used by contact" in str(e):
                return jsonify({"error": str(e)}), 400
            raise
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/emails", methods=["GET"])
def get_emails():
    """
    Get emails, optionally filtered by contacts
    
    Query Parameters:
        contacts: Optional list of contact names to filter by (can be specified multiple times)
        test_suffix: Optional test suffix for test database tables
        
    Returns:
        200: List of emails with their associated contacts
        500: Server error
    """
    try:
        contacts = request.args.getlist("contacts")
        test_suffix = request.args.get("test_suffix")
        db = get_db(test_suffix)
        emails = []
        for email_record, contacts_list in db.fetch_emails_with_contacts(contacts):
            emails.append({
                "id": email_record[0],
                "date": email_record[1].isoformat() if email_record[1] else None,
                "summary": email_record[2],
                "content": email_record[3],
                "contacts": [
                    {"name": name, "email": email} 
                    for name, email in contacts_list
                ]
            })
        return jsonify(emails), 200
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/emails", methods=["POST"])
def add_email():
    """Add a new email"""
    try:
        data = request.get_json()
        required_fields = ["contacts", "date", "content"]

        # Validate required fields
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Add email using database utility
        test_suffix = request.args.get("test_suffix")
        db = get_db(test_suffix)
        email_id = db.add_email(
            contacts=data["contacts"],
            date=data["date"],
            content=data["content"],
            summary=data.get("summary", ""),
        )

        return (
            jsonify(
                {
                    "message": "Email added successfully",
                    "email_id": email_id,
                }
            ),
            201,
        )
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/contacts/<name>", methods=["DELETE"])
def delete_contact(name: str):
    """
    Delete a contact by name and optional identifying information
    
    Path Parameters:
        name: Name of the contact to delete
        
    Query Parameters:
        contact_info: Optional contact information (email, phone, or linkedin) to help identify 
                     the correct contact when multiple contacts share the same name
        company: Optional company name to help identify the correct contact when multiple 
                contacts share the same name
        test_suffix: Optional test suffix for test database tables
        
    Returns:
        200: Contact successfully deleted
        404: Contact not found
        409: Multiple contacts found - additional identifying information needed
        500: Server error
    """
    try:
        test_suffix = request.args.get("test_suffix")
        contact_info = request.args.get("contact_info")
        company = request.args.get("company")
        
        db = get_db(test_suffix)
        success, error_message = db.delete_contact(
            name=name,
            contact_info=contact_info,
            company=company
        )
        
        if success:
            return jsonify({"message": f"Contact {name} deleted successfully"}), 200
        else:
            # If there's a specific error message (like multiple contacts found),
            # return 409 Conflict, otherwise 404 Not Found
            if isinstance(error_message, str) and "Multiple contacts found" in error_message:
                status_code = 409
            else:
                status_code = 404
            return jsonify({"error": error_message}), status_code
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5001)
