from custom_recognizers.my_address import MalaysiaAddressRecognizer


text = """
Name: Siti Rahimah binti Ismail

Address:
No 14, Jalan Taman Maju, 47810 Petaling Jaya, Selangor
"""


recognizer = MalaysiaAddressRecognizer()


results = recognizer.analyze(
    text=text,
    entities=["ADDRESS"]
)


for r in results:
    print(
        r.entity_type,
        "=>",
        text[r.start:r.end],
        r.score
    )