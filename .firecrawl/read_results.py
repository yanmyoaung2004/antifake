import json, os

d = json.load(open(os.path.join(os.path.dirname(__file__), "apicta-winners.json")))
print("=== APICTA WINNERS ===")
for r in d.get("data", {}).get("web", [])[:5]:
    print(f"  {r['title']}")
    print(f"  {r['url']}")
    print()

d = json.load(open(os.path.join(os.path.dirname(__file__), "anticounterfeit.json")))
print("=== ANTI-COUNTERFEIT ===")
for r in d.get("data", {}).get("web", [])[:8]:
    print(f"  {r['title']}")
    print(f"  {r['url']}")
    print()
