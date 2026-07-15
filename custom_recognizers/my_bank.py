from presidio_analyzer import PatternRecognizer, Pattern

class MalaysiaBankRecognizer(PatternRecognizer):
    def __init__(self):
        patterns=[
            Pattern(
                name="bank_account",
                regex=
                r"\b\d{4}-\d{4}-\d{4}\b",
                score=0.9
            )
        ]

        super().__init__(
            supported_entity="FINANCIAL",
            patterns=patterns,
            context=[
                "bank",
                "account",
                "acc",
                "cimb",
                "maybank",
                "public bank"
            ]
        )