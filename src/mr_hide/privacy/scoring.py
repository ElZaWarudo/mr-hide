"""Token-cost scoring ports and local implementations."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class TokenScorer(Protocol):
    metric: str

    def cost(self, value: str) -> int: ...


class TokenEncoding(Protocol):
    def encode(self, text: str) -> Sequence[int]: ...


class CharacterScorer:
    metric = "utf8-bytes"

    def cost(self, value: str) -> int:
        return len(value.encode("utf-8"))


class TiktokenScorer:
    def __init__(self, encoding: TokenEncoding, *, encoding_name: str) -> None:
        self._encoding = encoding
        self.metric = f"{encoding_name}-tokens"

    def cost(self, value: str) -> int:
        return len(self._encoding.encode(value))


class ConservativeScorer:
    def __init__(self, *scorers: TokenScorer) -> None:
        self._scorers = scorers or (CharacterScorer(),)
        self.metric = "max(" + ",".join(item.metric for item in self._scorers) + ")"

    def cost(self, value: str) -> int:
        return max(scorer.cost(value) for scorer in self._scorers)
