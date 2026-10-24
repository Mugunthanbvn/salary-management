"""Exact allocation of a whole number by shares (docs/12-seed-data.md sections 2 and 12)."""

from collections.abc import Sequence


def largest_remainder(total: int, weights: Sequence[int]) -> list[int]:
    """Split `total` into whole parts proportional to `weights`, adding up to `total` exactly.

    Each part gets the whole part of its quota; the units left over go to the largest
    remainders, and equal remainders to the earlier item, so the result is deterministic.
    Integer maths only. `weights` must not all be zero.
    """
    weight_sum = sum(weights)
    quotas = [divmod(total * weight, weight_sum) for weight in weights]
    parts = [whole for whole, _ in quotas]
    leftover = total - sum(parts)
    by_remainder = sorted(range(len(weights)), key=lambda index: (-quotas[index][1], index))
    for index in by_remainder[:leftover]:
        parts[index] += 1
    return parts
