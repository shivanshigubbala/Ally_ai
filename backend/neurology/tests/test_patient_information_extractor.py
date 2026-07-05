from backend.neurology.services.patient_information_extractor import (
    PatientInformationExtractor,
)


def test_import():
    extractor = PatientInformationExtractor()
    assert extractor is not None
