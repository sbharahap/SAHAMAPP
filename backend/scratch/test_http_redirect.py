import httpx

url = "https://news.google.com/rss/articles/CBMiW0FVX3lxTE5MRDhIX2hnQXNvNGFkOTBTOHVmd05pMjJNUFZHWW1lNlRTT2hNUUJESmhpX3h3Z0xuSG1VSkJxUWhTemV6TVdJdFRsaGtNR0dhTjJINDdXZHRIbjg?oc=5"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Apple Silicon Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

with httpx.Client(timeout=10.0, follow_redirects=True, headers=headers) as client:
    resp = client.get(url)
    print(resp.text)
