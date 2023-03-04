import re

AGENT_ID_PATTERN = re.compile(r"^\w+$")
URL_PATTERN = re.compile(
    r"^https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b"
    r"(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)$"
)


def validate_agent_id(agent_id: str):
    if not AGENT_ID_PATTERN.match(agent_id):
        raise ValueError("agent_id must be alpha numerics and underscores only.")


def validate_url(url: str):
    if url and not URL_PATTERN.match(url):
        raise ValueError("{url!r} is not a valid URL!")
