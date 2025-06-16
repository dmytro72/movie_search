import pytest
from movies.utils import normalize

@pytest.mark.parametrize("input_text, expected", [
    # Accented and non-ASCII characters
    ("Český lev", "cesky lev"),
    ("Žižka", "zizka"),
    ("Řehoř", "rehor"),
    ("Kůň", "kun"),
    ("Šťáva", "stava"),
    ("JÁNOŠÍK", "janosik"),
    ("123 ABC", "123 abc"),
    ("Normal text", "normal text"),
    ("", ""),

    # Punctuation and special characters
    ("Hello, world!", "hello world"),
    ("Well—this is fun.", "well this is fun"),
    ("Spaces     everywhere", "spaces everywhere"),
    ("Tabs\tand\nnewlines", "tabs and newlines"),
    ("Symbols: @#$%^&*()", "symbols"),
    ("Mix: Čau, světe! 123 — GO", "mix cau svete 123 go"),

    # Edge cases
    ("   Leading and trailing spaces   ", "leading and trailing spaces"),
    ("Multiple     spaces   inside", "multiple spaces inside"),
    ("Dashes - and — are removed", "dashes and are removed"),
    ("A    \t   mix \n of \r all \f spaces", "a mix of all spaces"),
])
def test_normalize(input_text, expected):
    assert normalize(input_text) == expected