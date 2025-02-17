from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from amltk.pipeline import Choice, Component, Sequential, Split


def test_heirarchical_str() -> None:
    pipeline = (
        Sequential(name="pipeline")
        >> Component(object, name="one", space={"v": [1, 2, 3]})
        >> Split(
            Component(object, name="x", space={"v": [4, 5, 6]}),
            Component(object, name="y", space={"v": [4, 5, 6]}),
            name="split",
        )
        >> Choice(
            Component(object, name="a", space={"v": [4, 5, 6]}),
            Component(object, name="b", space={"v": [4, 5, 6]}),
            name="choice",
        )
    )
    config = {
        "pipeline:one:v": 1,
        "pipeline:split:x:v": 4,
        "pipeline:split:y:v": 5,
        "pipeline:choice:__choice__": "a",
        "pipeline:choice:a:v": 6,
    }
    result = pipeline.configure(config)

    expected = (
        Sequential(name="pipeline")
        >> Component(object, name="one", config={"v": 1}, space={"v": [1, 2, 3]})
        >> Split(
            Component(object, name="x", config={"v": 4}, space={"v": [4, 5, 6]}),
            Component(object, name="y", config={"v": 5}, space={"v": [4, 5, 6]}),
            name="split",
        )
        >> Choice(
            Component(object, name="a", config={"v": 6}, space={"v": [4, 5, 6]}),
            Component(object, name="b", space={"v": [4, 5, 6]}),
            name="choice",
            config={"__choice__": "a"},
        )
    )

    assert result == expected


def test_heirarchical_str_with_predefined_configs() -> None:
    pipeline = (
        Sequential(name="pipeline")
        >> Component(object, name="one", config={"v": 1})
        >> Split(
            Component(object, name="x"),
            Component(object, name="y", space={"v": [4, 5, 6]}),
            name="split",
        )
        >> Choice(
            Component(object, name="a"),
            Component(object, name="b"),
            name="choice",
        )
    )

    config = {
        "pipeline:one:v": 2,
        "pipeline:one:w": 3,
        "pipeline:split:x:v": 4,
        "pipeline:split:x:w": 42,
        "pipeline:choice:__choice__": "a",
        "pipeline:choice:a:v": 3,
    }

    expected = (
        Sequential(name="pipeline")
        >> Component(object, name="one", config={"v": 2, "w": 3})
        >> Split(
            Component(object, name="x", config={"v": 4, "w": 42}),
            Component(object, name="y", space={"v": [4, 5, 6]}),
            name="split",
        )
        >> Choice(
            Component(object, name="a", config={"v": 3}),
            Component(object, name="b"),
            name="choice",
            config={"__choice__": "a"},
        )
    )

    result = pipeline.configure(config)
    assert result == expected


def test_config_transform() -> None:
    def _transformer_1(_: Mapping, __: Any) -> Mapping:
        return {"hello": "world"}

    def _transformer_2(_: Mapping, __: Any) -> Mapping:
        return {"hi": "mars"}

    pipeline = (
        Sequential(name="pipeline")
        >> Component(
            object,
            name="1",
            space={"a": [1, 2, 3]},
            config_transform=_transformer_1,
        )
        >> Component(
            object,
            name="2",
            space={"b": [1, 2, 3]},
            config_transform=_transformer_2,
        )
    )
    config = {
        "pipeline:1:a": 1,
        "pipeline:2:b": 1,
    }

    expected = (
        Sequential(name="pipeline")
        >> Component(
            object,
            name="1",
            space={"a": [1, 2, 3]},
            config={"hello": "world"},
            config_transform=_transformer_1,
        )
        >> Component(
            object,
            name="2",
            space={"b": [1, 2, 3]},
            config={"hi": "mars"},
            config_transform=_transformer_2,
        )
    )
    assert expected == pipeline.configure(config)
