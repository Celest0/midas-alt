from uuid import uuid4


def generate_id() -> str:
    """Generate a unique identifier string of UUID format."""
    return str(uuid4())
