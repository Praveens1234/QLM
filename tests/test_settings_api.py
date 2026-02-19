"""
Phase 4 Verification: API-based test of all new AI Settings endpoints.
"""
import httpx
import json

base = "http://localhost:8002/api/ai"
passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        print(f"  FAIL: {name} -- {detail}")

print("=== TEST 1: List Providers ===")
r = httpx.get(f"{base}/config/providers")
test("Status 200", r.status_code == 200, f"Got {r.status_code}")
providers = r.json()
test("Returns list", isinstance(providers, list))
if providers:
    p = providers[0]
    test("Provider has 'id'", "id" in p)
    test("Provider has 'name'", "name" in p)
    test("Provider has 'models'", "models" in p)
    test("Provider has 'has_key'", "has_key" in p)
    test("Provider has 'api_key_masked'", "api_key_masked" in p, f"keys: {list(p.keys())}")
    print(f"  Found {len(providers)} providers")

print("\n=== TEST 2: Active Config has provider_id ===")
r = httpx.get(f"{base}/config/active")
test("Status 200", r.status_code == 200)
active = r.json()
if active:
    test("Has provider_id", "provider_id" in active, f"keys: {list(active.keys())}")
    test("Has model", "model" in active)
    test("Has provider_name", "provider_name" in active)
    print(f"  Active: {json.dumps(active, indent=2)}")
else:
    print("  (No active config set)")

print("\n=== TEST 3: Add Provider ===")
r = httpx.post(f"{base}/config/providers", json={
    "name": "Test Provider",
    "base_url": "https://test.example.com/v1",
    "api_key": "sk-test-key-1234567890"
})
test("Status 200", r.status_code == 200, f"Got {r.status_code}: {r.text}")
test("Returns id", "id" in r.json() if r.status_code == 200 else False)

print("\n=== TEST 4: Update Provider (PUT) ===")
r = httpx.put(f"{base}/config/providers/test_provider", json={
    "name": "Test Provider Updated"
})
test("Status 200", r.status_code == 200, f"Got {r.status_code}: {r.text}")

# Verify update
r = httpx.get(f"{base}/config/providers")
updated = [p for p in r.json() if p["id"] == "test_provider"]
test("Name updated", updated and updated[0]["name"] == "Test Provider Updated",
     f"Got: {updated[0]['name'] if updated else 'NOT FOUND'}")

print("\n=== TEST 5: Set Active Config ===")
r = httpx.post(f"{base}/config/active", json={
    "provider_id": "test_provider",
    "model_id": "test-model-v1"
})
test("Status 200", r.status_code == 200, f"Got {r.status_code}: {r.text}")

# Verify
r = httpx.get(f"{base}/config/active")
active = r.json()
test("Active provider_id correct", active.get("provider_id") == "test_provider",
     f"Got: {active.get('provider_id')}")
test("Active model correct", active.get("model") == "test-model-v1",
     f"Got: {active.get('model')}")

print("\n=== TEST 6: Delete Provider ===")
r = httpx.delete(f"{base}/config/providers/test_provider")
test("Status 200", r.status_code == 200, f"Got {r.status_code}: {r.text}")

# Verify deletion
r = httpx.get(f"{base}/config/providers")
names = [p["id"] for p in r.json()]
test("Provider removed", "test_provider" not in names, f"Still found in: {names}")

# Active config should be cleared since active was test_provider
r = httpx.get(f"{base}/config/active")
test("Active config cleared", r.json() == {} or "provider_id" not in r.json(),
     f"Got: {r.text}")

print("\n=== TEST 7: Delete Non-existent Provider ===")
r = httpx.delete(f"{base}/config/providers/nonexistent")
test("Returns 404", r.status_code == 404, f"Got {r.status_code}")

print(f"\n{'='*50}")
print(f"RESULTS: {passed} passed, {failed} failed out of {passed+failed} tests")
print(f"{'='*50}")
