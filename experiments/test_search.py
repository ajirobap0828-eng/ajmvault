import requests

query = "pride and prejudice"
response = requests.get("https://openlibrary.org/search.json", params={"q": query})
data = response.json()
print(data)