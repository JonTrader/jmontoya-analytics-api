from ua_parser import user_agent_parser


def parse_user_agent(user_agent_string: str) -> dict[str, str | None]:
    """Parse a User-Agent string into browser and OS names.

    Returns `None` for either value if the input is empty or cannot be parsed.
    """
    if not user_agent_string:
        return {"browser": None, "os": None}

    parsed = user_agent_parser.Parse(user_agent_string)

    browser_family = parsed.get("user_agent", {}).get("family")
    browser_major = parsed.get("user_agent", {}).get("major")
    browser = " ".join(part for part in [browser_family, browser_major] if part).strip() or None

    os_family = parsed.get("os", {}).get("family")
    os_major = parsed.get("os", {}).get("major")
    os = " ".join(part for part in [os_family, os_major] if part).strip() or None

    return {"browser": browser, "os": os}
