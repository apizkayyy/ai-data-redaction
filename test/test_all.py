from custom_recognizers.register import create_analyzer
from custom_recognizers.entity_merger import merge_entities
from custom_recognizers.entity_filter import remove_address_false_positive


text = """
Name: Siti Rahimah binti Ismail

Address:
No 14, Jalan Taman Maju, 47810 Petaling Jaya, Selangor

IC:
900112-14-5678

Phone:
+60 12-345 6789

Bank:
8012-3456-7890
"""


analyzer = create_analyzer()


results = analyzer.analyze(
    text=text,
    language="en",
    entities=[
        "ADDRESS",
        "PERSON_NAME",
        "ID_NUMBER",
        "PHONE_NUMBER",
        "FINANCIAL",
        "PERSON",
        "LOCATION"
    ],
    score_threshold=0.5
)


results = merge_entities(results)


results = remove_address_false_positive(
    results,
    text
)


for r in results:
    print(
        r.entity_type,
        "=>",
        text[r.start:r.end],
        "score:",
        r.score
    )