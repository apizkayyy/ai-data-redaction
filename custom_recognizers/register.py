from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider

from .my_person import MalaysiaPersonRecognizer
from .my_address import MalaysiaAddressRecognizer
from .my_ic import MalaysiaICRecognizer
from .my_phone import MalaysiaPhoneRecognizer
from .my_bank import MalaysiaBankRecognizer


def create_analyzer():

    configuration = {
        "nlp_engine_name": "spacy",
        "models": [
            {
                "lang_code": "en",
                "model_name": "en_core_web_lg"
            }
        ]
    }


    provider = NlpEngineProvider(
        nlp_configuration=configuration
    )

    nlp_engine = provider.create_engine()


    analyzer = AnalyzerEngine(
        nlp_engine=nlp_engine
    )


    analyzer.registry.add_recognizer(
        MalaysiaPersonRecognizer()
    )


    analyzer.registry.add_recognizer(
        MalaysiaAddressRecognizer()
    )


    analyzer.registry.add_recognizer(
        MalaysiaICRecognizer()
    )


    analyzer.registry.add_recognizer(
        MalaysiaPhoneRecognizer()
    )


    analyzer.registry.add_recognizer(
        MalaysiaBankRecognizer()
    )


    return analyzer