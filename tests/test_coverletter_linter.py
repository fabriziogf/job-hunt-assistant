"""Tests for the deterministic cover letter linter (Chapter 3)."""

from job_hunt_assistant import CompanyFact, CompanyResearch
from job_hunt_assistant.coverletter import CoverLetter, LetterFormat, lint_cover_letter


def _research() -> CompanyResearch:
    return CompanyResearch(
        company="Northwind Commerce",
        hiring_manager_name="Dana Chen",
        facts=[CompanyFact(text="launched a same-day delivery network last quarter")],
    )


def _good_letter() -> CoverLetter:
    return CoverLetter(
        format=LetterFormat.LETTER,
        salutation="Dear Ms. Chen,",
        paragraphs=[
            "I'm a product manager applying for the PM role at Northwind Commerce.",
            "I have shipped recommender systems to millions of users.",
            "Your same-day delivery network is exactly the kind of logistics "
            "personalization problem I want to work on.",
            "I'll follow up next week — thank you for your consideration.",
        ],
        signoff="Sincerely,\nJordan Rivera",
    )


def test_clean_letter_has_no_errors():
    report = lint_cover_letter(
        _good_letter(), company="Northwind Commerce", research=_research()
    )
    assert not report.has_errors
    assert not report.warnings  # the good letter is clean


def test_generic_salutation_flagged():
    letter = _good_letter()
    letter.salutation = "Dear Hiring Manager,"
    report = lint_cover_letter(
        letter, company="Northwind Commerce", research=_research()
    )
    sal = report.by_code("generic_salutation")
    assert sal and "Dana Chen" in sal[0].message  # suggests the known name


def test_missing_company_name_is_error():
    letter = _good_letter()
    letter.paragraphs[0] = "I'm a product manager applying for the PM role."
    # remove the company mention from P3 too
    letter.paragraphs[2] = "Your delivery network is exactly my kind of problem."
    report = lint_cover_letter(letter, company="Northwind Commerce", research=_research())
    assert report.by_code("missing_company_name")
    assert report.has_errors


def test_placeholder_text_is_error():
    letter = _good_letter()
    letter.paragraphs[1] = "I led teams at [Previous Company] for years."
    report = lint_cover_letter(letter, company="Northwind Commerce", research=_research())
    assert report.by_code("placeholder_text")
    assert report.has_errors


def test_wrong_paragraph_count_flagged():
    letter = _good_letter()
    letter.paragraphs = letter.paragraphs[:3]  # only 3
    report = lint_cover_letter(letter, company="Northwind Commerce", research=_research())
    assert report.by_code("not_four_paragraphs")


def test_p3_not_specific_flagged():
    letter = _good_letter()
    letter.paragraphs[2] = "I am very passionate and a hard worker who delivers."
    report = lint_cover_letter(letter, company="Northwind Commerce", research=_research())
    assert report.by_code("p3_not_specific")


def test_no_research_warns():
    report = lint_cover_letter(_good_letter(), company="Northwind Commerce", research=None)
    assert report.by_code("no_company_research")


def test_referral_not_named_in_first_sentence():
    report = lint_cover_letter(
        _good_letter(),
        company="Northwind Commerce",
        research=_research(),
        referral="Sam Okafor",
    )
    assert report.by_code("referral_not_in_first_sentence")


def test_referral_named_passes():
    letter = _good_letter()
    letter.paragraphs[0] = (
        "Sam Okafor suggested I apply for the PM role at Northwind Commerce."
    )
    report = lint_cover_letter(
        letter,
        company="Northwind Commerce",
        research=_research(),
        referral="Sam Okafor",
    )
    assert not report.by_code("referral_not_in_first_sentence")


def test_too_long_flagged():
    letter = _good_letter()
    letter.paragraphs[1] = "word " * 400
    report = lint_cover_letter(letter, company="Northwind Commerce", research=_research())
    assert report.by_code("too_long")
