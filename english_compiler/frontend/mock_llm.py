"""Mock LLM frontend for Core IL generation.

This mock frontend generates Core IL v1.2 programs for testing.
It provides a deterministic alternative to the Claude frontend.
"""

from __future__ import annotations


# Static example code for experimental mode
_MOCK_PYTHON = '''if __name__ == "__main__":
    print("hello (mock)")
'''

_MOCK_JAVASCRIPT = '''console.log("hello (mock)");
'''

_MOCK_CPP = '''#include <iostream>

int main() {
    std::cout << "hello (mock)" << std::endl;
    return 0;
}
'''


class MockFrontend:
    """Mock frontend for testing without an LLM.

    This frontend doesn't extend BaseFrontend since it doesn't need
    the shared validation/retry logic - it generates deterministic output.
    """

    # Common exit phrases for mock classification
    _EXIT_PATTERNS = {
        "bye", "goodbye", "good bye", "see ya", "see you", "later",
        "done", "i'm done", "im done", "that's all", "thats all",
        "thanks", "thank you", "peace", "peace out", "cya",
        "stop", "end", "finish", "finished", "gtg", "gotta go",
        "i'm out", "im out", "leaving", "gn", "goodnight", "good night",
    }

    def __init__(self) -> None:
        pass

    def get_model_name(self) -> str:
        return "mock"

    def classify_exit_intent(self, user_input: str) -> str:
        """Classify if user input is an exit intent or code.

        For mock frontend, uses simple pattern matching since there's
        no real LLM available.

        Args:
            user_input: The user's input text.

        Returns:
            "EXIT" if the input matches known exit patterns, "CODE" otherwise.
        """
        normalized = user_input.lower().strip()
        # Remove punctuation for matching
        cleaned = "".join(c for c in normalized if c.isalnum() or c.isspace())

        # Check exact matches
        if cleaned in self._EXIT_PATTERNS:
            return "EXIT"

        # Check if input starts with common exit phrases
        for pattern in self._EXIT_PATTERNS:
            if cleaned.startswith(pattern + " ") or cleaned.startswith(pattern + ","):
                return "EXIT"

        return "CODE"

    def _call_api_text(self, user_message: str, system_prompt: str) -> str:
        """Call API expecting plain text response.

        For mock frontend, returns a simple explanation for errors,
        or the mock code for experimental mode.
        """
        # Check if this is an error explanation request
        if "Error:" in user_message:
            return (
                "The program encountered an error. "
                "Please check your code for issues and try again."
            )
        # Otherwise return generic mock response
        return "Mock response"

    def generate_code_direct(self, source_text: str, target: str) -> str:
        """Generate mock code for experimental mode.

        Returns static example code for each target language.
        """
        if target == "python":
            return _MOCK_PYTHON
        elif target == "javascript":
            return _MOCK_JAVASCRIPT
        elif target == "cpp":
            return _MOCK_CPP
        else:
            raise ValueError(f"Unsupported experimental target: {target}")

    def generate_coreil_from_text(self, source_text: str) -> dict:
        """Generate a mock Core IL v1.2 program from source text.

        This is a simple mock that recognizes a few keywords and generates
        basic Core IL programs. Used for testing without requiring an LLM.
        """
        text = source_text.lower()
        if "hello" in text:
            message = "hello"
        else:
            message = "unimplemented"

        ambiguities = []
        if "sort" in text:
            ambiguities = [
                {
                    "question": "Which sort order should be used?",
                    "options": ["stable", "unstable"],
                    "default": 0,
                }
            ]

        # Generate Core IL v1.2 (Print statement, not Call to "print")
        return {
            "version": "coreil-1.2",
            "ambiguities": ambiguities,
            "body": [
                {
                    "type": "Print",
                    "args": [
                        {"type": "Literal", "value": message}
                    ],
                }
            ],
        }


# Legacy function for backward compatibility
def generate_coreil_from_text(source_text: str) -> dict:
    """Generate a mock Core IL v1.2 program from source text.

    This is a convenience function that creates a MockFrontend instance
    and calls its generate_coreil_from_text method.
    """
    frontend = MockFrontend()
    return frontend.generate_coreil_from_text(source_text)
