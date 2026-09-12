def parse_openlibrary_book(raw_entry):
    "One raw Open Library doc in, one clean dict out."
    title = raw_entry.get("title")

    names = raw_entry.get("author_name", [])
    author = ", ".join(names) if names else "Unknown"

    return {
        "title": title,
        "author": author,
    }

def parse_book(raw_entry):
    "One raw Gutendex entry in, one clean dict out."
    title = raw_entry.get("title")

    names = [a.get("name", "Unknown") for a in raw_entry.get("authors", [])]
    author = ", ".join(names) if names else "Unknown"

    formats = raw_entry.get("formats", {})

    txt_url = formats.get("text/plain; charset=utf-8")
    if txt_url is None:
        for key, url in formats.items():
            if key.startswith("text/plain"):
                txt_url = url
                break

    epub_url = formats.get("application/epub+zip")

    return {
        "title": title,
        "author": author,
        "txt_url": txt_url,
        "epub_url": epub_url,
    }