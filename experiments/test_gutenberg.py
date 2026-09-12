import requests
from parse_book import parse_book

# --- Your fetch logic ---
response = requests.get("https://gutendex.com/books")
data = response.json()


# --- Step 3: The new logic ---
def parse_all_results(data):
    """Every raw entry in -> a list of clean dicts out."""
    books = []
    for entry in data.get("results", []):   # .get so a missing key can't crash
        books.append(parse_book(entry))
    return books


def display_menu(books, cap=10):
    """Print a numbered menu, or a friendly message if empty."""
    # 4. Keep the empty-results check you already have
    if not books:
        print("No books found.")
        return
        
    # 2. Slice the list before looping
    shown = books[:cap]
    
    # 5. Keep the core loop the same, just feeding it the sliced list
    for number, book in enumerate(shown, start=1):
        print(f"{number}. {book['title']} — {book['author']}")
        
    # 3. Compare lengths to decide whether to show a "showing X of Y" message
    if len(books) > cap:
        print(f"\nShowing {cap} of {len(books)} results")


# --- Main flow ---
books = parse_all_results(data)
display_menu(books)