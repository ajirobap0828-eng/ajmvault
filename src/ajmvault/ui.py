# AJMVAULT Visual Identity

BACKGROUND = "#0F172A"
SECONDARY_BACKGROUND = "#1E293B"

TEXT_PRIMARY = "#F5F1E8"
TEXT_SECONDARY = "#C8C1B5"

ACCENT_GOLD = "#D4A72C"
ACCENT_SAGE = "#7C9473"

SUCCESS = "#7FA66A"
ERROR = "#C75C5C"

from rich.console import Console
console = Console()

def show_brand():
    console.print()
    console.print(
        "AJMVAULT",
        style=f"bold {TEXT_PRIMARY}",
        justify="center"
    )
    console.print(
        "D I G I T A L   L I B R A R Y",
        style=f"bold {ACCENT_GOLD}",
        justify="center"
    )
    console.print(
        "────────────────────────────────────────",
        style=f"{TEXT_SECONDARY}",
        justify="center"
    )
    console.print()

if __name__ == "__main__":
    show_brand()    