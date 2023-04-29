import csv
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Final

import pytest

from htap.dataset import Dataset, DatasetLoadConfig
from htap.sql.parser import parse_schema
from htap.sql.schema import Schema

LIBRARY_SCHEMA: Final = """
DROP TABLE IF EXISTS author;
CREATE TABLE author (
    id integer PRIMARY KEY,
    name character varying(64) NOT NULL
);

DROP TABLE IF EXISTS book;
CREATE TABLE book (
    id integer PRIMARY KEY,
    title character varying(256) NOT NULL,
    price real,
    author_id integer NOT NULL REFERENCES author(id)
);
"""


@contextmanager
def create_library_dataset() -> Iterator[Dataset]:
    def to_tsv_line(*values: str) -> str:
        return "\t".join(values) + "\n"

    with tempfile.TemporaryDirectory() as tmpdirname:
        dataset_path = Path(tmpdirname)
        schema_path = dataset_path / "schema.sql"
        tables_path = dataset_path / "tsv"

        with open(schema_path, mode="w+", encoding="utf-8") as f:
            f.write(LIBRARY_SCHEMA)

        tables_path.mkdir(parents=True, exist_ok=True)

        with open(tables_path / "author.tsv", mode="w+", encoding="utf-8") as f:
            f.write(to_tsv_line("id", "name"))
            f.write(to_tsv_line("1", "alice"))
            f.write(to_tsv_line("2", "bob"))

        with open(tables_path / "book.tsv", mode="w+", encoding="utf-8") as f:
            f.write(to_tsv_line("id", "title", "price", "author_id"))
            f.write(to_tsv_line("1", "Alice in Wonderland", "100", "1"))
            f.write(to_tsv_line("2", "Code with Alice", r"\N", "1"))
            f.write(to_tsv_line("3", "Bob's cipher", "50", "2"))

        yield Dataset(
            name="library",
            schema_path=schema_path,
            tables_dir_path=tables_path,
            load_config=DatasetLoadConfig(
                delimiter="\t",
                skip_header=True,
                na_value=r"\N",
                quoting=csv.QUOTE_NONE,
                escape_char=None,
            ),
        )


@contextmanager
def create_partial_dataset() -> Iterator[Dataset]:
    with tempfile.TemporaryDirectory() as tmpdirname:
        dataset_path = Path(tmpdirname)
        schema_path = dataset_path / "schema.sql"
        tables_path = dataset_path / "tsv"

        with open(schema_path, mode="w+", encoding="utf-8") as f:
            f.write(LIBRARY_SCHEMA)

        tables_path.mkdir(parents=True, exist_ok=True)

        yield Dataset(
            name="library",
            schema_path=schema_path,
            tables_dir_path=tables_path,
            load_config=DatasetLoadConfig(
                delimiter="\t",
                skip_header=True,
                na_value=r"\N",
                quoting=csv.QUOTE_NONE,
                escape_char=None,
            ),
        )


@contextmanager
def create_invalid_dataset() -> Iterator[Dataset]:
    invalid_path = Path(__file__) / "invalid"

    yield Dataset(
        name="invalid",
        schema_path=invalid_path / "schema.sql",
        tables_dir_path=invalid_path / "tsv",
        load_config=DatasetLoadConfig(
            delimiter="\t",
            skip_header=True,
            na_value=r"\N",
            quoting=csv.QUOTE_NONE,
            escape_char=None,
        ),
    )


@pytest.fixture(name="schema")
def fixture_schema() -> Schema:
    return parse_schema(LIBRARY_SCHEMA, schema_name="library")


class TestDataset:
    def test_schema(self, schema: Schema) -> None:
        with create_library_dataset() as dataset:
            assert dataset.schema == schema
            assert dataset.tables == set(schema.tables)

    def test_get_dataframe(self, schema: Schema) -> None:
        with create_library_dataset() as dataset:
            author_df = dataset.get_dataframe("author")
            assert author_df.to_dict() == {
                "id": {0: 1, 1: 2},
                "name": {0: "alice", 1: "bob"},
            }

            book_df = dataset.get_dataframe(schema.get_table("book"))
            assert book_df.to_dict() == {
                "id": {0: 1, 1: 2, 2: 3},
                "title": {
                    0: "Alice in Wonderland",
                    1: "Code with Alice",
                    2: "Bob's cipher",
                },
                "price": {0: 100, 1: None, 2: 50},
                "author_id": {0: 1, 1: 1, 2: 2},
            }

    def test_invalid_schema(self) -> None:
        with create_invalid_dataset() as dataset:
            # Note that the dataset is loaded lazily
            with pytest.raises(ValueError):
                print(dataset.schema)

            with pytest.raises(ValueError):
                print(dataset.tables)

    def test_table_files_not_exist(self) -> None:
        with create_partial_dataset() as dataset:
            with pytest.raises(ValueError):
                dataset.get_dataframe("author")
