from presidio_analyzer import PatternRecognizer, Pattern


class MalaysiaAddressRecognizer(PatternRecognizer):

    def __init__(self):

        patterns = [
            Pattern(
                name="malaysia_address",

                regex=r"No\.?\s*\d+[A-Za-z\-]*.*?(?:Jalan|Jln|Lorong|Persiaran|Lebuh|Taman).*?\d{5}.*?(?:Selangor|Kuala Lumpur|Johor|Johor Bahru|Penang|Pulau Pinang|Perak|Kedah|Melaka|Negeri Sembilan|Pahang|Sabah|Sarawak)",

                score=0.95
            )
        ]


        super().__init__(
            supported_entity="ADDRESS",
            patterns=patterns
        )