"""Relation tools for Python."""

from itertools import dropwhile, groupby
from operator import itemgetter
from typing import Callable, Generic, Iterable, Iterator, Tuple, TypeVar

from more_itertools import peekable


__version__ = '0.9.2'
__author__ = 'Yu Mochizuki'
__author_email__ = 'ymoch.dev@gmail.com'


Key = TypeVar('Key')
Value = TypeVar('Value')
Left = TypeVar('Left')
Right = TypeVar('Right')

_EMPTY_LIST = []  # type: list
FIRST_ITEM_KEY = itemgetter(0)
DEFAULT_KEY = FIRST_ITEM_KEY


class _UnidirectionalFinder(Generic[Value, Key], Iterator[Iterator[Value]]):
    """
    This class finds items in `iterable` unidirectionally
    and groups them by the given `key`.

    Note that the `Key` must be 'comparable'
    (supports `__lt__()` and  `__gt__()`)
    and `iterable` must be sorted by `key`.

    Here are some normal cases.
    Collections are sorted by the first items.
    >>> iterable = [(0, 'a'), (1, 'b'), (1, 'c'), (2, 'd')]
    >>> finder = _UnidirectionalFinder(iterable, itemgetter(0))
    >>> finder.has_items
    True
    >>> finder.current_key()
    0

    When given a waiting key, then finds items and groups them by the key.
    >>> list(finder.find(1))
    [(1, 'b'), (1, 'c')]
    >>> finder.current_key()
    2

    When given passed keys, then cannot find items.
    >>> list(finder.find(1))
    []
    >>> list(finder.find(0))
    []

    When given too large keys, then cannot find items.
    Once given a too large key, the finder is exhausted.
    >>> list(finder.find(3))
    []
    >>> finder.has_items
    False
    >>> finder.current_key()
    Traceback (most recent call last):
        ...
    StopIteration

    When exhausted and given an existing key, then cannot find items.
    >>> list(finder.find(2))
    []

    Sequencial usage is also supported.
    >>> iterable = [(0, 'a'), (1, 'b'), (1, 'c'), (2, 'd'), (3, 'e')]
    >>> finder = _UnidirectionalFinder(iterable, itemgetter(0))
    >>> finder.current_key()
    0
    >>> list(next(finder))
    [(0, 'a')]
    >>> finder.current_key()
    1
    >>> list(next(finder))
    [(1, 'b'), (1, 'c')]
    >>> finder.current_key()
    2
    >>> list(finder.find(3))
    [(3, 'e')]
    >>> finder.current_key()
    Traceback (most recent call last):
        ...
    StopIteration
    >>> next(finder)
    Traceback (most recent call last):
        ...
    StopIteration

    Here are some seminormal cases.
    When given an empty collection, then cannot find any items.
    >>> finder = _UnidirectionalFinder([], itemgetter(0))
    >>> finder.has_items
    False
    >>> list(finder.find(0))
    []
    >>> finder.current_key()
    Traceback (most recent call last):
        ...
    StopIteration

    When given a not sorted `iterable`,
    then stops finding at reverse-ordering segments.
    >>> iterable = [(0, 'a'), (2, 'b'), (1, 'c'), (3, 'd')]
    >>> finder = _UnidirectionalFinder(iterable, itemgetter(0))
    >>> list(finder.find(1))
    []
    >>> finder.current_key()
    2
    >>> list(finder.find(2))
    [(2, 'b')]
    >>> list(finder.find(3))
    [(3, 'd')]
    """
    def __init__(
        self,
        iterable: Iterable[Value],
        key: Callable[[Value], Key],
    ) -> None:
        """Initialize"""
        self._groups = peekable(groupby(iterable, key))

    def find(self, key: Key) -> Iterator[Value]:
        """Find items that have the given key."""
        self.seek_to(key)

        if not self.has_items:
            return iter(_EMPTY_LIST)

        group_key, group_items = self._groups.peek()
        if group_key > key:
            return iter(_EMPTY_LIST)

        next(self)
        return group_items

    def seek_to(self, key: Key) -> None:
        """Seek to the given key."""
        seeked_groups = dropwhile(lambda group: group[0] < key, self._groups)
        self._groups = peekable(seeked_groups)

    @property
    def has_items(self) -> bool:
        """Check if the iterator has items."""
        return bool(self._groups)

    def current_key(self) -> Key:
        """
        Returns the current key.
        When exhausted, then throws StopIteration.
        """
        return self._groups.peek()[0]

    def __next__(self) -> Iterator[Value]:
        """
        Returns the current value and move to the next.
        When exhausted, then throws StopIteration.
        """
        return next(self._groups)[1]


def relate_one_to_many(
    lhs: Iterable[Left],
    rhs: Iterable[Right],
    lhs_key: Callable[[Left], Key]=DEFAULT_KEY,
    rhs_key: Callable[[Right], Key]=DEFAULT_KEY,
) -> Iterator[Tuple[Left, Iterator[Right]]]:
    """
    Relates `rhs` items to each `lhs` items.

    Note that:
    - `Key` must be 'comparable' (supports `__lt__()` and  `__gt__()`).
    - `lhs` must be sorted by keys that `lhs_key` provides.
    - `rhs` must be sorted by keys that `rhs_key` provides.

    `lhs_key` and `rhs_key` are optional.
    When not given, then relates `rhs` to `lhs`
    by their first items (`left[0]` and `right[0]`).

    Here are some normal cases.
    These collections are sorted by the first items.
    >>> lhs = [(0, 'a'), (1, 'b'), (2, 'c')]
    >>> rhs = [(1, 's'), (2, 't'), (2, 'u'), (3, 'v')]

    When not given any keys,
    then relates `rhs` to `lhs` by their first items.
    >>> relations = relate_one_to_many(lhs, rhs)
    >>> for left, right in relations:
    ...     left, list(right)
    ((0, 'a'), [])
    ((1, 'b'), [(1, 's')])
    ((2, 'c'), [(2, 't'), (2, 'u')])

    When given custom keys, then relates `rhs` to `lhs` by that keys.
    Note that the custom keys *must not* break the key ordering.
    >>> relations = relate_one_to_many(
    ...     lhs, rhs,
    ...     lhs_key=lambda l: l[0] * 2,
    ...     rhs_key=lambda r: r[0] - 1)
    >>> for left, right in relations:
    ...     left, list(right)
    ((0, 'a'), [(1, 's')])
    ((1, 'b'), [(3, 'v')])
    ((2, 'c'), [])

    Here are some seminormal cases.
    When given an empty `lhs`, then returns an empty iterator.
    >>> relations = relate_one_to_many([], [(1, 's')])
    >>> list(relations)
    []

    When given an empty `rhs`, then returns an iterator that relates nothing.
    >>> relations = relate_one_to_many([(1, 'a')], [])
    >>> for left, right in relations:
    ...     left, list(right)
    ((1, 'a'), [])

    When given unordered `lhs`, then stops relationing
    at reverse-ordering segments.
    >>> lhs = [(0, 'a'), (2, 'b'), (1, 'c'), (4, 'd'), (3, 'e')]
    >>> rhs = [(1, 's'), (2, 't'), (2, 'u'), (3, 'v'), (4, 'w')]
    >>> relations = relate_one_to_many(lhs, rhs)
    >>> for left, right in relations:
    ...     left, list(right)
    ((0, 'a'), [])
    ((2, 'b'), [(2, 't'), (2, 'u')])
    ((1, 'c'), [])
    ((4, 'd'), [(4, 'w')])
    ((3, 'e'), [])

    When given unordered `rhs`, then stops relationing
    at reverse-ordering segments.
    >>> lhs = [(0, 'a'), (1, 'b'), (2, 'c'), (3, 'd'), (4, 'e')]
    >>> rhs = [(1, 's'), (3, 't'), (3, 'u'), (2, 'v'), (4, 'w')]
    >>> relations = relate_one_to_many(lhs, rhs)
    >>> for left, right in relations:
    ...     left, list(right)
    ((0, 'a'), [])
    ((1, 'b'), [(1, 's')])
    ((2, 'c'), [])
    ((3, 'd'), [(3, 't'), (3, 'u')])
    ((4, 'e'), [(4, 'w')])
    """
    rhs_finder = _UnidirectionalFinder(rhs, rhs_key)
    return ((l, rhs_finder.find(lhs_key(l))) for l in lhs)


def left_join(
    lhs: Iterable[Left],
    rhs: Iterable[Right],
    lhs_key: Callable[[Left], Key]=DEFAULT_KEY,
    rhs_key: Callable[[Right], Key]=DEFAULT_KEY,
) -> Iterator[Tuple[Iterator[Left], Iterator[Right]]]:
    """
    Join two iterables like SQL left joining.
    While SQL left joining returns all the combinations,
    this returns the pair of items.

    The arguments are very similar to `relate_one_to_many`.
    See `relate_one_to_many` doc for more information.

    This function is equivalent to below:
    - Groups `lhs` by `lhs_key`.
    - Run `relate_one_to_many` with that group as `lhs` and `rhs`.

    Here are some normal cases.
    Note that the `right` can empty, like SQL left joining.
    >>> lhs = [(1, 'a'), (1, 'b'), (2, 'c'), (4, 'd')]
    >>> rhs = [(1, 's'), (1, 't'), (3, 'u'), (4, 'v')]
    >>> relations = left_join(lhs, rhs)
    >>> for left, right in relations:
    ...     list(left), list(right)
    ([(1, 'a'), (1, 'b')], [(1, 's'), (1, 't')])
    ([(2, 'c')], [])
    ([(4, 'd')], [(4, 'v')])

    Custom keys are acceptable.
    >>> relations = left_join(
    ...     lhs, rhs,
    ...     lhs_key=lambda l: l[0] * 2,
    ...     rhs_key=lambda r: r[0] + 1)
    >>> for left, right in relations:
    ...     list(left), list(right)
    ([(1, 'a'), (1, 'b')], [(1, 's'), (1, 't')])
    ([(2, 'c')], [(3, 'u')])
    ([(4, 'd')], [])

    Here is a seminormal cases.
    When given empty `lhs`, returns the empty iterator.
    >>> relations = left_join([], [(1, 's')])
    >>> list(relations)
    []
    """
    lhs_groups = groupby(lhs, lhs_key)
    relations = relate_one_to_many(lhs_groups, rhs, FIRST_ITEM_KEY, rhs_key)
    return ((left, right) for ((_, left), right) in relations)


def outer_join(
    lhs: Iterable[Left],
    rhs: Iterable[Right],
    lhs_key: Callable[[Left], Key]=DEFAULT_KEY,
    rhs_key: Callable[[Right], Key]=DEFAULT_KEY,
) -> Iterator[Tuple[Iterator[Left], Iterator[Right]]]:
    """
    Join two iterables preserving all existing keys.
    In contrast to `left_join`, this preserve keys that are only in `rhs`.

    The arguments are very similar to `relate_one_to_many`.
    See `relate_one_to_many` doc for more information.

    Here are some normal cases.
    Note that all existing keys are covered and
    both `left` and `right` can be empty.
    >>> lhs = [(1, 'a'), (1, 'b'), (2, 'c'), (4, 'd')]
    >>> rhs = [(1, 's'), (1, 't'), (3, 'u'), (4, 'v')]
    >>> relations = outer_join(lhs, rhs)
    >>> for left, right in relations:
    ...     list(left), list(right)
    ([(1, 'a'), (1, 'b')], [(1, 's'), (1, 't')])
    ([(2, 'c')], [])
    ([], [(3, 'u')])
    ([(4, 'd')], [(4, 'v')])

    When given custom keys, then joins by them.
    >>> relations = relate_one_to_many(
    ...     lhs, rhs,
    ...     lhs_key=lambda l: l[0] * 2,
    ...     rhs_key=lambda r: r[0] + 1)
    >>> for left, right in relations:
    ...     left, list(right)
    ((1, 'a'), [(1, 's'), (1, 't')])
    ((1, 'b'), [])
    ((2, 'c'), [(3, 'u')])
    ((4, 'd'), [])

    When given long tail `lhs`, then returns the empty tail for the right.
    >>> relations = outer_join([(1, 'a'), (2, 'b')], [(1, 's')])
    >>> for left, right in relations:
    ...     list(left), list(right)
    ([(1, 'a')], [(1, 's')])
    ([(2, 'b')], [])

    When given long tail `rhs`, then returns the empty tail for the left.
    >>> relations = outer_join([(1, 'a')], [(1, 's'), (2, 't')])
    >>> for left, right in relations:
    ...     list(left), list(right)
    ([(1, 'a')], [(1, 's')])
    ([], [(2, 't')])

    Here are some seminormal cases.
    When given empty `lhs`,
    then returns an iterator that all left items are empty.
    >>> relations = outer_join([], [(1, 's')])
    >>> for left, right in relations:
    ...     list(left), list(right)
    ([], [(1, 's')])

    When given empty `rhs`,
    then returns an iterator that all right items are empty
    >>> relations = outer_join([(1, 'a')], [])
    >>> for left, right in relations:
    ...     list(left), list(right)
    ([(1, 'a')], [])
    """
    lhs_finder = _UnidirectionalFinder(lhs, lhs_key)
    rhs_finder = _UnidirectionalFinder(rhs, rhs_key)

    while lhs_finder.has_items:
        if not rhs_finder.has_items:
            yield next(lhs_finder), iter(_EMPTY_LIST)
            continue

        key_curr = min(lhs_finder.current_key(), rhs_finder.current_key())
        yield lhs_finder.find(key_curr), rhs_finder.find(key_curr)

    while rhs_finder.has_items:
        yield iter(_EMPTY_LIST), next(rhs_finder)


def inner_join(
    lhs: Iterable[Left],
    rhs: Iterable[Right],
    lhs_key: Callable[[Left], Key]=DEFAULT_KEY,
    rhs_key: Callable[[Right], Key]=DEFAULT_KEY,
) -> Iterator[Tuple[Iterator[Left], Iterator[Right]]]:
    """
    Join two iterables like SQL inner joining.

    This function's behavior is very similar to `left_join`.
    See `left_join` doc first.

    In contrast to `left_join`, `right` cannot be empty,
    like SQL inner joining.

    Here are some normal cases.
    >>> lhs = [(1, 'a'), (1, 'b'), (2, 'c'), (4, 'd')]
    >>> rhs = [(1, 's'), (1, 't'), (3, 'u'), (4, 'v')]
    >>> relations = inner_join(lhs, rhs)
    >>> for left, right in relations:
    ...     list(left), list(right)
    ([(1, 'a'), (1, 'b')], [(1, 's'), (1, 't')])
    ([(4, 'd')], [(4, 'v')])

    Custom keys are acceptable.
    >>> relations = inner_join(
    ...     lhs, rhs,
    ...     lhs_key=lambda l: l[0] * 2,
    ...     rhs_key=lambda r: r[0] + 1)
    >>> for left, right in relations:
    ...     list(left), list(right)
    ([(1, 'a'), (1, 'b')], [(1, 's'), (1, 't')])
    ([(2, 'c')], [(3, 'u')])

    Here is a seminormal cases.
    When given empty `lhs`, returns the empty iterator.
    >>> relations = inner_join([], [(1, 's')])
    >>> list(relations)
    []
    """
    left_joined = left_join(lhs, rhs, lhs_key, rhs_key)
    relations = ((left, peekable(right)) for (left, right) in left_joined)
    return ((left, right) for (left, right) in relations if right)
