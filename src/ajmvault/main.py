import json
import os
import re
import requests
from ajmvault.parse_book import parse_book, parse_openlibrary_book
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tkinter import filedialog
import tkinter as tk
from ajmvault.ui import console, show_brand

BACKGROUND = "#0F172A"
SECONDARY_BACKGROUND = "#1E293B"

TEXT_PRIMARY = "#F5F1E8"
TEXT_SECONDARY = "#C8C1B5"

ACCENT_GOLD = "#D4A72C"
ACCENT_SAGE = "#7C9473"

SUCCESS = "#7FA66A"
ERROR = "#C75C5C"

# 1. module-level setting: where downloads land ("." = current folder)
download_path = "."

CONFIG_FILE = "config.json"


# --- load saved settings on startup, falling back to defaults safely ---
def load_config():
    global download_path

    if not os.path.exists(CONFIG_FILE):
        return  # first run ever, nothing to load — keep default "."

    try:
        with open(CONFIG_FILE, "r") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        print("Warning: config.json is unreadable, using default settings.")
        return

    saved_path = data.get("download_path", ".")

    if os.path.isdir(saved_path):
        download_path = saved_path
    else:
        print(f"Warning: saved path '{saved_path}' no longer exists, using default.")


# --- save current settings to disk ---
def save_config():
    data = {"download_path": download_path}
    try:
        with open(CONFIG_FILE, "w") as file:
            json.dump(data, file)
    except OSError as err:
        print(f"Warning: couldn't save config: {err}")


# --- fetch from Open Library instead of Gutenberg ---
def fetch_openlibrary(query):
    response = requests.get(
        "https://openlibrary.org/search.json",
        params={"q": query},
    )
    response.raise_for_status()
    return response.json()

# --- Step 2: fetch, driven by the user's query ---
def fetch_books(query):
    """Fetch raw Gutendex results for a given search query."""
    response = requests.get(
        "https://gutendex.com/books",
        params={"search": query},
    )
    response.raise_for_status()
    return response.json()


# --- Step 3: parse every result into a clean dict ---
def parse_all_results(data):
    books = []
    for entry in data.get("results", []):
        books.append(parse_book(entry))
    return books

def parse_all_openlibrary_results(data):
    books = []
    for entry in data.get("docs", []):
        books.append(parse_openlibrary_book(entry))
    return books

def display_menu(books, cap=10):
    from rich.table import Table
    from rich.panel import Panel

    shown = books[:cap]

    table = Table(
        show_header=True,
        header_style=f"bold {ACCENT_GOLD}",
        border_style=ACCENT_GOLD,
        expand=True,
        padding=(0, 1),
    )

    table.add_column("#", style=f"bold {ACCENT_GOLD}", width=4, justify="center")
    table.add_column("TITLE", style=f"bold {TEXT_PRIMARY}")
    table.add_column("AUTHOR", style=TEXT_SECONDARY)

    for i, book in enumerate(shown, start=1):
        title = book.get("title", "Unknown title")
        author = book.get("author", "Unknown author")

        table.add_row(
            str(i),
            title,
            author
        )

    console.print()
    console.print(
        Panel(
            table,
            title="[bold]SEARCH RESULTS[/bold]",
            title_align="left",
            border_style=ACCENT_GOLD,
            padding=(1, 1),
        )
    )
    console.print()

    return shown

# --- check Gutenberg for a downloadable match, only when a book is picked ---
def find_gutenberg_match(title, author):
    try:
        data = fetch_books(title)
    except requests.RequestException:
        return None

    results = data.get("results", [])
    if not results:
        return None

    # only accept a result if the author genuinely matches too
    first_author_word = author.split()[0].lower() if author else ""

    for entry in results:
        candidate = parse_book(entry)
        candidate_author = candidate.get("author", "").lower()
        if first_author_word and first_author_word in candidate_author:
            return candidate

    return None  # title existed on Gutenberg, but never by this author

# --- make a title safe to use as a Windows filename ---
def safe_filename(title):
    name = re.sub(r'[<>:"/\\|?*]', "_", title or "")
    name = name.strip(" .")
    return name or "book"


# --- 5. uniqueness checked at the FULL path, not just the bare filename ---
def unique_filename(filepath):
    directory = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    base, ext = os.path.splitext(filename)
    counter = 2
    while os.path.exists(filepath):
        filepath = os.path.join(directory, f"{base} ({counter}){ext}")
        counter += 1
    return filepath



# --- 4. download respects download_path via os.path.join ---
def download_book(book, format_choice):
    from rich.progress import (
        Progress,
        BarColumn,
        TextColumn,
        DownloadColumn,
        TransferSpeedColumn,
        TimeRemainingColumn,
    )
    from rich.panel import Panel

    if format_choice == "epub" and book.get("epub_url"):
        url = book["epub_url"]
        extension = ".epub"
    elif format_choice == "txt" and book.get("txt_url"):
        url = book["txt_url"]
        extension = ".txt"
    else:
        console.print(
            Panel(
                "Sorry, that format isn't available for this book.",
                title="FORMAT UNAVAILABLE",
                border_style=ERROR,
            )
        )
        return

    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504]
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))

    filename = safe_filename(book["title"]) + extension
    full_path = unique_filename(
        os.path.join(download_path, filename)
    )

    console.print()

    download_info = (
        f"[bold {TEXT_PRIMARY}]{book['title']}[/bold {TEXT_PRIMARY}]\n"
        f"[{TEXT_SECONDARY}]Format:[/{TEXT_SECONDARY}] "
        f"[{ACCENT_GOLD}]{extension[1:].upper()}[/{ACCENT_GOLD}]\n"
        f"[{TEXT_SECONDARY}]Destination:[/{TEXT_SECONDARY}] "
        f"[{TEXT_PRIMARY}]{os.path.abspath(full_path)}[/{TEXT_PRIMARY}]\n\n"
        f"[bold {ACCENT_GOLD}]Press Ctrl+C to cancel the download.[/bold {ACCENT_GOLD}]"
    )

    console.print(
        Panel(
            download_info,
            title="DOWNLOAD",
            title_align="left",
            border_style=ACCENT_GOLD,
            padding=(1, 2),
        )
    )

    try:
        with session.get(
            url,
            timeout=(10, 60),
            stream=True
        ) as response:

            response.raise_for_status()

            total_size = int(
                response.headers.get("Content-Length", 0)
            )

            with open(full_path, "wb") as file:

                with Progress(
                    TextColumn("[bold]Downloading[/bold]"),
                    BarColumn(),
                    TextColumn(
                        "[progress.percentage]{task.percentage:>5.1f}%"
                    ),
                    DownloadColumn(),
                    TransferSpeedColumn(),
                    TimeRemainingColumn(),
                ) as progress:

                    task = progress.add_task(
                        book["title"],
                        total=total_size if total_size else None
                    )

                    for chunk in response.iter_content(
                        chunk_size=8192
                    ):
                        if chunk:
                            file.write(chunk)
                            progress.update(
                                task,
                                advance=len(chunk)
                            )

    except KeyboardInterrupt:
        console.print()
        console.print(
            Panel(
                "Download cancelled.",
                title="CANCELLED",
                border_style=ERROR,
            )
        )

        if os.path.exists(full_path):
            os.remove(full_path)

        return

    except requests.RequestException:
        console.print()
        console.print(
            Panel(
                "Unable to download the book.\n"
                "Please check your internet connection and try again.",
                title="DOWNLOAD FAILED",
                border_style=ERROR,
            )
        )
        return

    except OSError as err:
        console.print()
        console.print(
            Panel(
                f"Couldn't save the file:\n{err}",
                title="SAVE ERROR",
                border_style=ERROR,
            )
        )
        return

    console.print()
    console.print(
        Panel(
            f"[bold {SUCCESS}]✓ Download complete[/bold {SUCCESS}]\n\n"
            f"[{TEXT_SECONDARY}]Saved to:[/{TEXT_SECONDARY}]\n"
            f"[{TEXT_PRIMARY}]{os.path.abspath(full_path)}[/{TEXT_PRIMARY}]",
            title="SUCCESS",
            title_align="left",
            border_style=SUCCESS,
            padding=(1, 2),
        )
    )
    
# --- 2 + 7. the path command: popup picker (no arg) or typed path (with arg) ---
def handle_path(argument=""):
    global download_path

    print(f"Current download path: {os.path.abspath(download_path)}")

    if argument:
        new_path = argument.strip()
    else:
        # hide tkinter's blank root window, only show the folder popup
        root = tk.Tk()
        root.withdraw()
        new_path = filedialog.askdirectory(title="Choose download folder")
        root.destroy()

        if not new_path:
            print("No folder selected — path unchanged.")
            return

    if os.path.isdir(new_path):
        download_path = new_path
        save_config()
        print(f"Download path updated to: {os.path.abspath(new_path)}")
    else:
        print(f"That folder doesn't exist: {new_path}")


# --- ask the user which format to download, only offering what's available ---
def choose_format(book):
    has_txt = bool(book.get("txt_url"))
    has_epub = bool(book.get("epub_url"))

    if not has_txt and not has_epub:
        return None  # download_book will print the "no format" message

    if has_txt and not has_epub:
        return "txt"

    if has_epub and not has_txt:
        return "epub"

    # both exist -> ask
    choice = input("Which format? (txt/epub, default txt): ").strip().lower()
    if choice == "epub":
        return "epub"
    return "txt"  # empty input, "txt", or anything invalid -> default to txt

# --- search command: fetch -> parse -> display -> pick -> download ---
def handle_search(query):
    title, author = split_title_and_author(query)
    search_query = f"{title} {author}".strip()  # Open Library takes one combined string

    try:
        data = fetch_openlibrary(search_query)
    except requests.RequestException as err:
        print(f"Oops! Reconnect and try again.")
        return

    books = parse_all_openlibrary_results(data)
    shown = display_menu(books)
    if not shown:
        return

    choice = input("\nEnter a number to download, or press Enter to skip: ").strip()

    if not choice:
        return

    try:
        number = int(choice)
    except ValueError:
        print("That's not a number — skipping.")
        return

    if not 1 <= number <= len(shown):
        print(f"Please enter a number between 1 and {len(shown)}.")
        return

    picked = shown[number - 1]

    print(f"\nChecking Gutenberg for '{picked['title']}'...")
    match = find_gutenberg_match(picked["title"], picked["author"])

    if match is None or (not match.get("txt_url") and not match.get("epub_url")):
        print("Sorry, no free downloadable copy of this book was found on Gutenberg.")
        return

    format_choice = choose_format(match)
    if format_choice is None:
        print("Sorry, this book has no txt or epub format to download.")
        return

    download_book(match, format_choice)

# --- split "title by author" into separate parts, if written that way ---
def split_title_and_author(query):
    lowered = query.lower()
    if " by " in lowered:
        index = lowered.index(" by ")
        title = query[:index].strip()
        author = query[index + 4:].strip()
        return title, author
    return query.strip(), ""

# --- help text, ---
def show_help():
    from rich.panel import Panel
    from rich.table import Table

    table = Table(
        show_header=True,
        header_style=f"bold {ACCENT_GOLD}",
        border_style=ACCENT_GOLD,
        expand=True,
    )

    table.add_column("COMMAND", style=f"bold {ACCENT_GOLD}", width=16)
    table.add_column("DESCRIPTION", style=TEXT_PRIMARY)

    table.add_row("search (optional)", "Search for a book")
    table.add_row("path", "View or change download folder")
    table.add_row("help", "Show this help menu")
    table.add_row("quit", "Exit AJMVAULT")

    console.print()
    console.print(
        Panel(
            table,
            title="[bold]AJMVAULT COMMANDS[/bold]",
            title_align="left",
            border_style=ACCENT_GOLD,
            padding=(1, 1),
        )
    )
    console.print()

# --- Step 4: the CLI loop ---
def main():
    load_config()
    show_brand()
    console.print("Type [bold]help[/bold] for commands.\n")
    while True:
        raw = input("ajmvault> ").strip()

        if not raw:
            print("Unknown command. Type 'help' for options.")
            continue
        parts = raw.split(" ", 1)
        command = parts[0].lower()
        argument = parts[1].strip() if len(parts) > 1 else ""

        if command == "quit":
            print("Goodbye!")
            break
        elif command == "help":
            show_help()
        elif command == "path":
            handle_path(argument)
        elif command == "search":
            # still works if someone types "search" explicitly
            if not argument:
                print("Usage: search <query>")
            else:
                handle_search(argument)
        else:
            # not a known command -> treat the WHOLE line as a search query
            handle_search(raw)

        
        
if __name__ == "__main__":
    main()