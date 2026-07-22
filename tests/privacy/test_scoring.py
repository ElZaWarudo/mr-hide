from __future__ import annotations

from mr_hide.privacy.scoring import CharacterScorer, ConservativeScorer, TiktokenScorer


class FixedScorer:
    def __init__(self, value: int) -> None:
        self.value = value
        self.metric = f"fixed-{value}"

    def cost(self, value: str) -> int:
        return self.value


class WordEncoding:
    def encode(self, text: str) -> list[int]:
        return list(range(len(text.split())))


def test_tiktoken_scorer_uses_explicitly_injected_encoding() -> None:
    scorer = TiktokenScorer(WordEncoding(), encoding_name="fixture")

    assert scorer.cost("hello") == 1
    assert scorer.cost("hello world") >= 2
    assert scorer.metric == "fixture-tokens"


def test_conservative_scorer_uses_worst_available_measurement() -> None:
    scorer = ConservativeScorer(FixedScorer(2), FixedScorer(5), CharacterScorer())

    assert scorer.cost("x") == 5
    assert scorer.metric == "max(fixed-2,fixed-5,utf8-bytes)"
