from pipeline.word_grouper import group_words_by_segments


def test_group_words_basic():
    """Basic test for word grouping by midpoint."""
    words = [
        {"word": "Hello", "start": 0.0, "end": 0.5},
        {"word": "World", "start": 0.6, "end": 1.0},
    ]
    segments = [{"start": 0.0, "end": 1.1, "text": "Hello World"}]

    result = group_words_by_segments(words, segments)

    assert len(result) == 1
    assert len(result[0]["words"]) == 2
    assert result[0]["words"][0]["word"] == "Hello"
    assert result[0]["words"][1]["word"] == "World"


def test_group_words_split():
    """Test words split into different segments."""
    words = [
        {"word": "One", "start": 0.0, "end": 0.4},
        {"word": "Two", "start": 0.6, "end": 1.0},
    ]
    segments = [
        {"start": 0.0, "end": 0.5, "text": "One"},
        {"start": 0.5, "end": 1.1, "text": "Two"},
    ]

    result = group_words_by_segments(words, segments)

    assert len(result) == 2
    assert result[0]["words"][0]["word"] == "One"
    assert result[1]["words"][0]["word"] == "Two"


def test_group_words_tolerance():
    """Test words slightly outside boundary but within tolerance."""
    words = [
        {"word": "Edge", "start": 0.95, "end": 1.05},  # Midpoint: 1.0
    ]
    segments = [
        {"start": 0.0, "end": 0.95, "text": "Context"}  # Tolerance 0.1 makes it end at 1.05
    ]

    result = group_words_by_segments(words, segments, tolerance=0.1)

    assert len(result) == 1
    assert result[0]["words"][0]["word"] == "Edge"


def test_empty_input():
    """Test with empty segments or words."""
    assert group_words_by_segments([], [{"start": 0, "end": 1, "text": "test"}]) == []
    assert group_words_by_segments([{"word": "test", "start": 0, "end": 1}], []) == []
