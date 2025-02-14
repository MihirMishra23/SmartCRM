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
    """Add a new contact"""
    try:
        data = request.get_json()
        required_fields = ["name", "contact_methods"]

        # Validate required fields
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Add contact using database utility
        test_suffix = request.args.get("test_suffix")
        db = get_db(test_suffix)
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
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/emails", methods=["GET"])
def get_emails():
    """Get emails, optionally filtered by contacts"""
    try:
        contacts = request.args.getlist("contacts")
        test_suffix = request.args.get("test_suffix")
        db = get_db(test_suffix)
        emails = []
        for email in db.fetch_emails(contacts):
            emails.append(
                {
                    "id": email[0],
                    "date": email[1].isoformat() if email[1] else None,
                    "summary": email[2],
                    "content": email[3],
                }
            )
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
