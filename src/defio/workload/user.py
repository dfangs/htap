from __future__ import annotations

from typing import final
from uuid import UUID, uuid4

from attrs import define, field


@final
@define(frozen=True)
class User:
    """
    Represents a user of a `Workload` serial unit.

    Each user is identified by a UUID (and hence globally unique),
    but may optionally be labeled by some string or integer value.
    Note that this label is excluded from the equality test.
    """

    uuid: UUID
    label: str | int | None = field(default=None, eq=False)

    @staticmethod
    def random() -> User:
        """Returns a new user with a random UUID and no label."""
        return User(uuid=uuid4())

    @staticmethod
    def with_label(label: str) -> User:
        """
        Creates a new user with a random UUID and the given label.

        For clarity, while a user's label may technically be an integer,
        this method only accepts string labels. If possible, integer
        labels should be reserved for autogenerated labels.
        """
        return User(uuid=uuid4(), label=label)

    def relabel(self, label: str | int) -> User:
        """
        Returns a new user with the same UUID but relabeled into
        the given label.
        """
        return User(uuid=self.uuid, label=label)
