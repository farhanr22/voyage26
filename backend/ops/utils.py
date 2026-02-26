"""
Shared utility functions for Tally API operations.
"""

import requests
from flask import current_app


def fetch_tally_submissions(api_key, form_id):
    """
    Fetch submissions from Tally API.

    Args:
        api_key: Tally API bearer token
        form_id: Tally form ID

    Returns:
        Dict containing API response with questions and submissions
    """

    url = f"https://api.tally.so/forms/{form_id}/submissions?limit=300"
    headers = {"Authorization": f"Bearer {api_key}"}

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    return response.json()


def build_question_map(questions, required_keys):
    """
    Build a mapping from question title to question ID.

    Args:
        questions: List of question objects from Tally API
        required_keys: List of keys to look for (e.g., ["name", "phone", ...])

    Returns:
        Dict mapping key -> question_id
    """

    question_map = {}

    for question in questions:
        title = question.get("title")
        q_id = question.get("id")

        if title in required_keys and q_id:
            question_map[title] = q_id

    return question_map


def extract_answer_from_response(responses, question_id):
    """
    Extract answer value from responses list given a question ID.

    Args:
        responses: List of response objects from a submission
        question_id: Tally question ID to look for

    Returns:
        Answer value or None if not found
    """

    for response in responses:
        if response.get("questionId") == question_id:
            answer = response.get("answer")
            # Handle array answers (from MULTIPLE_CHOICE, DROPDOWN)
            if isinstance(answer, list) and len(answer) > 0:
                return answer[0]
            return answer
    return None


def extract_record_from_submission(submission, question_map, field_mapping):
    """
    Extract a flat record dict from a Tally submission.

    Args:
        submission: Submission object from Tally API
        question_map: Dict mapping our keys to Tally question IDs
        field_mapping: Dict mapping output keys to internal keys

    Returns:
        Dict with SubID, SubAt, and mapped field values
    """

    responses = submission.get("responses", [])

    def get_answer(key):
        q_id = question_map.get(key)
        if q_id:
            return extract_answer_from_response(responses, q_id)
        return None

    record = {
        "SubID": submission["id"],
        "SubAt": submission["submittedAt"],
    }

    for output_key, internal_key in field_mapping.items():
        record[output_key] = get_answer(internal_key)

    return record


def ingest_submissions(
    api_response,
    model_class,
    field_mapping,
    process_func,
    existing_ids_field="SubID",
):
    """
    Generic function to ingest submissions into database.

    Args:
        api_response: Response from Tally API
        model_class: Peewee model class to insert into
        field_mapping: Dict mapping model fields to internal keys
        process_func: Function to process record before insertion
                      Returns (processed_record, should_insert) tuple
        existing_ids_field: Field name to check for existing records

    Returns:
        Boolean indicating if any new records were added
    """

    questions = api_response.get("questions", [])
    submissions = api_response.get("submissions", [])

    required_keys = list(field_mapping.values())
    question_map = build_question_map(questions, required_keys)

    new_records_added = False

    with model_class._meta.database.atomic():
        existing_ids = {
            getattr(rec, existing_ids_field)
            for rec in model_class.select(getattr(model_class, existing_ids_field))
        }

        for submission in submissions:
            if submission["id"] not in existing_ids:
                record = extract_record_from_submission(
                    submission, question_map, field_mapping
                )
                processed_record, should_insert = process_func(record)

                if should_insert:
                    model_class.create(**processed_record)
                    new_records_added = True

                    name_value = processed_record.get("Name", "Unknown")
                    print(f"  -> New Record: {name_value}")

    return new_records_added
