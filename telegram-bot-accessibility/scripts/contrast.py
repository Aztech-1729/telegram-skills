"""Opaque sRGB contrast checks; not a complete accessibility audit."""
import argparse
import json
import re


def luminance(color):
    if not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        raise ValueError("Use an opaque six-digit #RRGGBB sRGB color")
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in channels]
    return sum(c * weight for c, weight in zip(linear, (.2126, .7152, .0722)))


def contrast(first, second):
    low, high = sorted((luminance(first), luminance(second)))
    return (high + .05) / (low + .05)


def text_color(background):
    return max(("#000000", "#ffffff"), key=lambda color: contrast(background, color))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("foreground")
    parser.add_argument("background")
    args = parser.parse_args()
    try:
        ratio = contrast(args.foreground, args.background)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps({"ratio": ratio, "normal_text_4_5": ratio >= 4.5,
                      "large_text_3": ratio >= 3, "best_black_or_white": text_color(args.background)}))


if __name__ == "__main__":
    main()
