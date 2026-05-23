"""Compatibility wrapper.

The old minimal guide generated the deprecated A/B/C route. Use the single
current final builder instead.
"""

from build_zombie_almighty import build_all


def build():
    return build_all()


if __name__ == "__main__":
    build()
