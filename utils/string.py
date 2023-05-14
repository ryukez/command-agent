from typing import List


def parse_comma_separated_text(s: str) -> List[str]:
    splits = s.split(",")
    if len(splits) > 1:
        return splits
    else:
        # Handle "、" in Japanese
        splits = s.split("、")

    return list(map(lambda s: s.strip(), splits))
