from presidio_analyzer import PatternRecognizer, Pattern

class MalaysiaPersonRecognizer(PatternRecognizer):

    def __init__(self):
        patterns = [
            Pattern(
                name="malay_full_name",
                regex=
                r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:bin|binti|a\/l|a\/p)\s+[A-Z][a-z]+\b",
                score=0.95
            ),

            Pattern(
                name="chinese_name",
                regex=
                r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b",
                score=0.75
            ),

            Pattern(
                name="malaysia_indian_name",
                regex=r"\b[A-Z][a-z]+\s+(?:"
                      r"[A-Z][a-z]+\s+)?"
                      r"(?:A/L|A/P|a/l|a/p)\s+"
                      r"[A-Z][a-z]+\b",
                score=0.85
            )
        ]

        super().__init__(
            supported_entity="PERSON_NAME",
            patterns=patterns,
            context=[
                "name",
                "employee",
                "customer",
                "applicant",
                "owner"
            ]
        )