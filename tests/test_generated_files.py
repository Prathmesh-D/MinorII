"""Tests for generated benchmark file utilities."""

from __future__ import annotations

import pytest

from src.benchmark.generated_files import (
    BYTES_PER_MB,
    GENERATED_PROFILES,
    build_generated_dataset,
    parse_group_size_mb,
)


def test_parse_group_size_mb_valid_values() -> None:
    assert parse_group_size_mb("F1_1MB") == 1
    assert parse_group_size_mb("F5_100MB") == 100
    assert parse_group_size_mb("Benchmark_50MB") == 50


def test_parse_group_size_mb_invalid_value() -> None:
    with pytest.raises(ValueError):
        parse_group_size_mb("F1_small")


def test_build_generated_dataset_creates_expected_files(tmp_path) -> None:
    files, summary = build_generated_dataset(tmp_path, ["F1_1MB"])

    assert len(files) == len(GENERATED_PROFILES)
    assert summary.file_count == len(GENERATED_PROFILES)
    assert summary.total_bytes == len(GENERATED_PROFILES) * BYTES_PER_MB

    target_group_dir = summary.root_dir / "F1_1MB"
    assert target_group_dir.exists()

    for profile, extension in GENERATED_PROFILES:
        expected = target_group_dir / f"{profile}_1MB.{extension}"
        assert expected.exists()
        assert expected.stat().st_size == BYTES_PER_MB


def test_build_generated_dataset_honors_stop_signal(tmp_path) -> None:
    with pytest.raises(RuntimeError):
        build_generated_dataset(
            tmp_path,
            ["F1_1MB"],
            should_stop=lambda: True,
        )
