# Celestia syntax validator

A Python utility for validating the syntax of Celestiaʼs
Deep Sky Catalog (.dsc), Solar System Catalog (.ssc) and
Star Catalog (.stc) files. The syntax is based on the supported features in
the pre-release version 1.7 of Celestia.

## Requirements

A sufficiently-recent Python is required. This was developed using
Python 3.12, earlier versions may not work. No additional libraries are
needed.

## Running the program

The program can either act on a single file:

```bash
./validate.py path/to/catalog.ssc
```

It can operate on a directory:

```bash
./validate.py path/to/celestia/data
```

It can also validate an add-on in a .zip file:

```bash
./validate.py path/to/addon.zip
```

If the `-v` or `--verbose` flags are passed, the program will display
additional non-fatal messages, currently this indicates where spectral type
parsing is truncated.

An exit code of 0 indicates no warnings or errors were found. An exit code of
1 indicates errors were found by the parser. Other exit codes indicate an
unexpected error during execution, e.g. file access restrictions.

## Limitations

Currently this only performs syntax validation and basic property existence
checks. It does not do checks of interdependent property values, such as
verifying that the ring system inner radius is less than the outer radius. It
also does not validate that referenced files (e.g. textures, meshes) exist,
and does not check whether referenced objects exist. Catalog file entries with
the "Modify" disposition further skip most existence checks.

Validation of archive files is limited to the .zip format, other archive
formats such as .rar are not supported.

## License

[GPL-2.0-or-later](LICENSES/GPL-2.0-or-later.txt)
