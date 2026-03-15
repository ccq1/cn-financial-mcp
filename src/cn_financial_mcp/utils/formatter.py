"""
Data formatting utilities for converting pandas DataFrames to JSON responses.

All MCP tool responses are returned as JSON strings for Claude to parse.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd


def df_to_json(
    df: pd.DataFrame,
    orient: str = "records",
    max_rows: int | None = None,
    date_format: str = "iso",
) -> str:
    """
    Convert a pandas DataFrame to a JSON string suitable for MCP tool response.

    Args:
        df: The DataFrame to convert.
        orient: pandas to_json orient parameter. Default 'records' for list of dicts.
        max_rows: Maximum number of rows to include. None for all.
        date_format: Date format for datetime columns.

    Returns:
        JSON string representation of the DataFrame.
    """
    if df is None or df.empty:
        return json.dumps([], ensure_ascii=False)

    if max_rows is not None and len(df) > max_rows:
        df = df.head(max_rows)

    # Convert datetime columns to string to avoid serialization issues
    for col in df.select_dtypes(include=["datetime64", "datetimetz"]).columns:
        df[col] = df[col].astype(str)

    return df.to_json(orient=orient, force_ascii=False, date_format=date_format)


def dict_to_json(data: dict[str, Any] | list[dict[str, Any]]) -> str:
    """
    Convert a dict or list of dicts to a JSON string.

    Args:
        data: Dictionary or list of dictionaries to convert.

    Returns:
        JSON string.
    """
    return json.dumps(data, ensure_ascii=False, default=str)


def error_response(message: str, tool_name: str = "") -> str:
    """
    Create a standardized error response JSON string.

    Args:
        message: Error description.
        tool_name: Name of the tool that errored.

    Returns:
        JSON string with error info.
    """
    return json.dumps(
        {
            "error": True,
            "message": message,
            "tool": tool_name,
        },
        ensure_ascii=False,
    )


def truncate_df(df: pd.DataFrame, max_rows: int = 50) -> pd.DataFrame:
    """Truncate a DataFrame to max_rows, adding a note if truncated."""
    if len(df) <= max_rows:
        return df
    return df.head(max_rows)
