from flask import Blueprint, jsonify, request, current_app
from ..models import Reg_Data, ItemsTaken

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/student-data", methods=["POST"])
def get_student_data():
    """
    API endpoint that returns all verified student data
    for the static site generator.
    """

    data = request.get_json()
    print('current password: ', current_app.config.get("API_PASSWORD"))
    print("recevied paswrod : ", data.get("password"))

    # Check for the API password
    if not data or data.get("password") != current_app.config.get("API_PASSWORD"):
        return jsonify({"error": "Unauthorized"}), 401

    # Fetch all verified profiles from the database
    profiles = list(Reg_Data.select().where(Reg_Data.StudentID.is_null(False)).dicts())

    # Fetch all dispatched items
    # Create a dictionary lookup for items: { 'STUDENTID': ['T-SHIRT', 'TIFFIN'], ... }
    items_by_student = {}
    items_query = ItemsTaken.select(ItemsTaken.StudentID, ItemsTaken.Item).tuples()

    for student_id, item in items_query:
        if student_id not in items_by_student:
            items_by_student[student_id] = []
        items_by_student[student_id].append(item)

    # Process the data into the final format
    students_list = []

    for p in profiles:
        student_id = p.get("StudentID")
        items_received = items_by_student.get(student_id, [])

        students_list.append(
            {
                "id": student_id,
                "name": p.get("Name"),
                "batch": p.get("Stream"),
                "food": p.get("FoodPref"),
                "tshirt": (
                    "Opted out"
                    if not p.get("TShirtSize")
                    else f"Size : {p.get('TShirtSize')}"
                ),
                "paid": int(p.get("Paid") or 0),
                "payable": int(p.get("Payable") or 0),
                "items_rec": ", ".join(items_received) if items_received else "None",
            }
        )

    return jsonify({"data": students_list})
