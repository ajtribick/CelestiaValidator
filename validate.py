#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Andrew Tribick
# SPDX-License-Identifier: GPL-2.0-or-later

"""Validates Celestia add-ons"""

import argparse
import pathlib
import sys
import zipfile

from typing import TextIO

from celvalidate import (
    DSCParser,
    MessageLevel,
    ParsingError,
    SSCParser,
    STCParser,
    TokenFileParser,
)

_PARSER_MAPPING: dict[str, type] = {
    ".dsc": DSCParser,
    ".ssc": SSCParser,
    ".stc": STCParser,
}


def _process_messages(
    filename: pathlib.Path, parser: TokenFileParser, is_verbose: bool
) -> int:
    exit_code = 0
    for message in parser.messages:
        if is_verbose or message.level > MessageLevel.INFO:
            print(f"{filename}:{message}")
        if message.level > MessageLevel.INFO:
            exit_code = 1
    return exit_code


def _process_file(
    text: TextIO, filename: str, parser_type: type, is_verbose: bool
) -> int:
    "Process a DSC file"
    parser = parser_type(text)
    try:
        parser.parse()
    except ParsingError:
        pass

    return _process_messages(filename, parser, is_verbose)


def _process_directory(path: pathlib.Path, is_verbose: bool) -> int:
    exit_code = 0
    for file in path.rglob("*.*"):
        if (
            parser_type := _PARSER_MAPPING.get(file.suffix.casefold(), None)
        ) is not None:
            relative_name = file.relative_to(path)
            with open(file, "rt", encoding="utf-8", errors="replace") as f:
                exit_code = max(
                    exit_code, _process_file(f, relative_name, parser_type, is_verbose)
                )
    return exit_code


def _process_archive(path: pathlib.Path, is_verbose: bool) -> int:
    exit_code = 0
    with zipfile.ZipFile(path, mode="r") as zf:
        for zipinfo in zf.infolist():
            if zipinfo.is_dir():
                continue
            if "__MACOSX" in zipinfo.filename:
                # ignore MacOS resource forks
                continue
            file_path = zipfile.Path(zf, zipinfo.filename)
            if (
                parser_type := _PARSER_MAPPING.get(file_path.suffix.casefold(), None)
            ) is None:
                continue
            with file_path.open(mode="rt", encoding="utf-8", errors="replace") as f:
                exit_code = max(
                    exit_code,
                    _process_file(f, zipinfo.filename, parser_type, is_verbose),
                )
    return exit_code


def _process(path: pathlib.Path, is_verbose: bool) -> int:
    if path.is_dir():
        return _process_directory(path, is_verbose)
    if path.is_file():
        suffix = path.suffix.casefold()
        if suffix == ".zip":
            return _process_archive(path, is_verbose)
        if (parser_type := _PARSER_MAPPING.get(suffix, None)) is not None:
            with open(path, "rt", encoding="utf-8", errors="replace") as f:
                return _process_file(f, path.name, parser_type, is_verbose)
    print(f"Could not open {str(path)!r}", file=sys.stderr)
    return 1


argparser = argparse.ArgumentParser(
    prog="validate",
    description="Validate Celestia data files",
)

argparser.add_argument(
    "path", type=pathlib.Path, help="path to file, directory or archive"
)
argparser.add_argument(
    "-v",
    "--verbose",
    action="store_true",
    help="display additional informational messages",
)

args = argparser.parse_args()
sys.exit(_process(args.path, args.verbose))
