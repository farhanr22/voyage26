from datetime import datetime

def format_datetime_simple(value: str):
    """
    Jinja2 filter to parse a timestamp string (e.g., '2025-10-14T15:30:00')
    and format it into a specific format (e.g., '03:30 PM - 14 Oct')
    """
    if not value:
        return ""
    
    try:
        # Parse into an object
        dt_object = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
        
        # Format for output 
        return dt_object.strftime('%I:%M\u00A0%p %d\u00A0%b')
        
    except (ValueError, TypeError):
        # If any issues, return as is
        return value