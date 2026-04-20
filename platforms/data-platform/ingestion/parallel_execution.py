from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Iterable, TypeVar

T = TypeVar('T')
R = TypeVar('R')


def ordered_parallel_map(
    items: Iterable[T],
    worker: Callable[[T], R],
    *,
    max_workers: int,
) -> list[R]:
    ordered_items = list(items)
    if len(ordered_items) <= 1 or max_workers <= 1:
        return [worker(item) for item in ordered_items]

    results_by_index: dict[int, R] = {}
    with ThreadPoolExecutor(max_workers=min(max_workers, len(ordered_items))) as executor:
        future_by_index = {
            executor.submit(worker, item): index
            for index, item in enumerate(ordered_items)
        }
        for future, index in future_by_index.items():
            results_by_index[index] = future.result()
    return [results_by_index[index] for index in range(len(ordered_items))]


__all__ = ['ordered_parallel_map']
