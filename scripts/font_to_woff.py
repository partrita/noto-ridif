#!/usr/bin/env python3
"""Create compressed WOFF and WOFF2 web fonts for EPUB embedding and the web."""

from pathlib import Path

import click
from fontTools.ttLib import TTFont

SUPPORTED_FORMATS = ("woff", "woff2")


def convert_font(source: Path, output: Path, flavor: str) -> int:
    """Write *source* as *output* with the requested WOFF flavor."""
    font = TTFont(str(source))
    try:
        font.flavor = flavor
        font.save(str(output))
    finally:
        font.close()
    return output.stat().st_size


@click.command()
@click.argument("font", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("."),
    show_default=True,
    help="Directory for the generated web fonts.",
)
@click.option(
    "--basename",
    default=None,
    help="Output basename without extension (default: input font stem).",
)
@click.option(
    "--formats",
    default="woff,woff2",
    show_default=True,
    help="Comma-separated formats to generate (woff, woff2).",
)
def main(font: Path, output_dir: Path, basename: str | None, formats: str) -> None:
    """Convert a TTF/OTF font to WOFF and/or WOFF2."""
    requested = [item.strip().lower() for item in formats.split(",") if item.strip()]
    invalid = [item for item in requested if item not in SUPPORTED_FORMATS]
    if invalid:
        raise click.BadParameter(
            f"unsupported format(s): {', '.join(invalid)}; choose from {', '.join(SUPPORTED_FORMATS)}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = basename or font.stem

    for flavor in requested:
        output = output_dir / f"{stem}.{flavor}"
        try:
            size = convert_font(font, output, flavor)
        except ImportError as err:
            raise click.ClickException(
                f"{flavor} requires the 'brotli' package: {err}"
            ) from err
        click.echo(f"✓ {output} ({size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    main()
