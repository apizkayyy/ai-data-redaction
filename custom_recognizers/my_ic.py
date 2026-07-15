from presidio_analyzer import PatternRecognizer, Pattern


class MalaysiaICRecognizer(PatternRecognizer):

    def __init__(self):
        patterns=[
            Pattern(
                name="malaysia_ic",
                regex=
                r"\b\d{6}-\d{2}-\d{4}\b",
                score=0.95
            ),

            Pattern(
                name="malaysia_ic_without_dash",
                regex=
                r"\b\d{12}\b",
                score=0.85
            )
        ]

        super().__init__(
            supported_entity="ID_NUMBER",
            patterns=patterns,
            context=[
                "ic",
                "identity",
                "mykad",
                "nric"
            ]
        )