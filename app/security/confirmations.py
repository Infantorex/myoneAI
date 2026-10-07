"""User confirmation prompt and policy manager.
"""

import logging
from typing import Callable, Optional

logger = logging.getLogger("myoneAI.security.confirmations")


class ConfirmationManager:
    """Handles requesting and validating user confirmations."""

    def __init__(self, default_policy: bool = True) -> None:
        self.default_policy = default_policy

    def request_confirmation(self, action_name: str, details: str, prompt_fn: Optional[Callable[[str], bool]] = None) -> bool:
        """Prompt user for confirmation before executing sensitive tasks."""
        logger.info("Requesting confirmation for: %s (%s)", action_name, details)
        if prompt_fn:
            return prompt_fn(f"Are you sure you want to {action_name} ({details})?")
        return False
