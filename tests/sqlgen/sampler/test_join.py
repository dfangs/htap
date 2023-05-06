from collections.abc import Sequence, Set
from itertools import combinations
from typing import Final

import pytest

from defio.sql.ast.from_clause import JoinType
from defio.sql.schema import Schema, Table, TableColumn
from defio.sqlgen.ast.from_clause import GenAliasedTable, GenFromClause, GenJoin
from defio.sqlgen.sampler.join import JoinEdge, JoinSampler, JoinSamplerConfig
from defio.utils.random import Randomizer

NUM_ITERS: Final = 1000


class TestJoinSampler:
    @pytest.mark.parametrize(
        "max_num_tables, join_types, join_type_weights",
        [
            (1, [JoinType.INNER_JOIN], None),
            (2, [JoinType.INNER_JOIN, JoinType.LEFT_OUTER_JOIN], [0.8, 0.2]),
            (4, list(set(JoinType) - {JoinType.CROSS_JOIN}), None),
        ],
    )
    def test_sample_join(
        self,
        imdb_schema: Schema,
        max_num_tables: int,
        join_types: Sequence[JoinType],
        join_type_weights: Sequence[float] | None,
    ) -> None:
        join_sampler = JoinSampler(
            schema=imdb_schema,
            rng=Randomizer(),
            config=JoinSamplerConfig(
                max_num_tables=max_num_tables,
                join_types=join_types,
                join_types_weights=join_type_weights,
                with_self_join=True,
            ),
        )

        sampled_joins = [join_sampler.sample_joins() for _ in range(NUM_ITERS)]

        expected_join_types = (
            {
                join_type
                for join_type, weight in zip(join_types, join_type_weights)
                if weight > 0
            }
            if join_type_weights is not None
            else set(join_types)
        )

        # Check whether the config is enforced

        assert all(
            len(joins.unique_tables) <= max_num_tables for joins in sampled_joins
        )

        assert all(
            TestJoinSampler._get_sampled_tables(joins) <= set(imdb_schema.tables)
            for joins in sampled_joins
        )

        assert all(
            TestJoinSampler._get_sampled_join_types(joins) <= expected_join_types
            for joins in sampled_joins
        )

    @staticmethod
    def _get_sampled_tables(joins: GenFromClause) -> Set[Table]:
        return {unique_table.table for unique_table in joins.unique_tables}

    @staticmethod
    def _get_sampled_join_types(joins: GenFromClause) -> Set[JoinType]:
        match joins:
            case GenAliasedTable():
                return set()
            case GenJoin():
                return (
                    {joins.join_type}
                    | TestJoinSampler._get_sampled_join_types(joins.left)
                    | TestJoinSampler._get_sampled_join_types(joins.right)
                )
            case _:
                raise RuntimeError("Should not reach here")


class TestJoinEdge:
    def test_equality_and_hash(self, imdb_schema: Schema) -> None:
        # Test for all pairs of table-columns, since the schema is small
        for table in imdb_schema.tables:
            for first, second in combinations(table.table_columns, 2):
                forward, reverse = JoinEdge(first, second), JoinEdge(second, first)
                assert forward == reverse
                assert hash(forward) == hash(reverse)

    def test_get_possible_join_edges(self, imdb_schema: Schema) -> None:
        # Test the whole schema
        for first_table in imdb_schema.tables:
            actual = JoinEdge.get_possible_join_edges(imdb_schema, first_table)

            expected = {
                JoinEdge(
                    TableColumn(first_table, first_column),
                    TableColumn(second_table, second_column),
                )
                for first_column in first_table.columns
                for second_table, second_column in (
                    imdb_schema.relationships.get_possible_joins(
                        first_table, first_column
                    )
                )
            }

            assert actual == expected
