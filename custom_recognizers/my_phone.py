from presidio_analyzer import PatternRecognizer, Pattern

class MalaysiaPhoneRecognizer(PatternRecognizer):
    def __init__(self):
        patterns=[
            Pattern(
                name="malaysia_mobile",
                regex=r"""
                (?:
                    \+60\s?
                    |
                    0
                )
                1[0-9]
                [-\s]?
                [0-9]{3,4}
                [-\s]?
                [0-9]{3,4}
                """,
                score=0.95
            ),

            Pattern(
                name="malaysia_landline",
                regex=
                r"\b0\d-\d{4}\s?\d{4}\b",
                score=0.85
            )
        ]

        super().__init__(
            supported_entity="PHONE_NUMBER",
            patterns=patterns,
            context=[
                "phone",
                "mobile",
                "tel",
                "telephone"
            ]
        )