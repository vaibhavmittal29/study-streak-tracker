"""End-to-end smoke test script using only Python standard library.

Can run against local server or public live deployment.
Handles Render free-tier cold starts by retrying the initial health check
up to 90 seconds.
"""

import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from urllib.error import HTTPError, URLError


def request(url: str, method: str = "GET", data: dict | None = None, timeout: float = 30.0):
    """Make HTTP request and return (status_code, body_text, json_data, headers)."""
    headers = {"User-Agent": "StudyStreakTrackerSmokeTest/1.0"}
    encoded_data = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        encoded_data = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status_code = resp.status
            body = resp.read().decode("utf-8", errors="replace")
            resp_headers = dict(resp.headers)
            parsed_json = None
            try:
                parsed_json = json.loads(body)
            except Exception:
                pass
            return status_code, body, parsed_json, resp_headers
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        parsed_json = None
        try:
            parsed_json = json.loads(body)
        except Exception:
            pass
        return e.code, body, parsed_json, dict(e.headers)


def run_smoke_test(base_url: str) -> bool:
    """Execute end-to-end smoke test suite against target server."""
    base_url = base_url.rstrip("/")
    print("\n" + "=" * 70)
    print(f"  RUNNING SMOKE TEST ON: {base_url}")
    print("=" * 70)

    # --- 1. Cold-start tolerant health check (up to 90s) ---
    print("\n[STEP 1/13] Checking /api/health (with cold-start tolerance up to 90s)...")
    start_time = time.time()
    health_ok = False
    status_code, body, data, _ = 0, "", None, {}

    while time.time() - start_time < 90:
        try:
            status_code, body, data, _ = request(f"{base_url}/api/health", timeout=10.0)
            if status_code == 200 and data and data.get("status") == "ok":
                elapsed = time.time() - start_time
                print(f"  [PASS] /api/health responded 200 OK in {elapsed:.1f}s")
                health_ok = True
                break
        except (URLError, TimeoutError, ConnectionError) as err:
            elapsed = time.time() - start_time
            print(f"  ... waiting for server to wake up ({elapsed:.0f}s elapsed: {err})")
        time.sleep(3)

    if not health_ok:
        print(
            "  [FAIL] Server failed to respond to /api/health within 90s "
            f"(last status: {status_code})"
        )
        return False

    all_passed = True

    def check(title: str, condition: bool, detail: str = "") -> bool:
        nonlocal all_passed
        if condition:
            print(f"  [PASS] {title}")
            return True
        else:
            print(f"  [FAIL] {title} -> {detail}")
            all_passed = False
            return False

    # --- 2. GET / ---
    print("\n[STEP 2/13] Checking Dashboard HTML at / ...")
    sc, body, _, _ = request(f"{base_url}/")
    check(
        "GET / returns 200 with HTML",
        sc == 200 and "Study Streak Tracker" in body,
        f"status: {sc}",
    )

    # --- 3. GET /docs ---
    print("\n[STEP 3/13] Checking Swagger API Docs at /docs ...")
    sc, body, _, _ = request(f"{base_url}/docs")
    check("GET /docs returns 200", sc == 200 and "swagger" in body.lower(), f"status: {sc}")

    # --- 4. GET /api/streak ---
    print("\n[STEP 4/13] Checking Streak Metrics at /api/streak ...")
    sc, _, streak_data, _ = request(f"{base_url}/api/streak")
    streak_keys = ["current_streak", "longest_streak", "studied_today", "streak_at_risk", "today"]
    check(
        "GET /api/streak returns valid shape",
        sc == 200 and streak_data and all(k in streak_data for k in streak_keys),
        f"status: {sc}, data: {streak_data}",
    )
    today_str = (
        streak_data.get("today", date.today().isoformat())
        if streak_data
        else date.today().isoformat()
    )

    # --- 5. POST /api/sessions ---
    print(f"\n[STEP 5/13] Logging test session for date {today_str} ...")
    session_payload = {
        "subject": "Smoke Test Session",
        "duration_minutes": 25,
        "date": today_str,
        "notes": "Automated verification session",
    }
    sc, _, created, _ = request(f"{base_url}/api/sessions", method="POST", data=session_payload)
    session_id = created.get("id") if created else None
    check(
        "POST /api/sessions creates session (201)",
        sc == 201 and session_id is not None,
        f"status: {sc}, body: {created}",
    )

    # --- 6. Confirm list & studied_today ---
    print("\n[STEP 6/13] Verifying session list & studied_today flag ...")
    sc, _, list_data, _ = request(f"{base_url}/api/sessions?limit=5")
    sc_s, _, after_streak, _ = request(f"{base_url}/api/streak")
    has_test_session = list_data and any(
        s.get("id") == session_id for s in list_data.get("items", [])
    )
    studied_now = after_streak.get("studied_today") if after_streak else None
    check(
        "Created session in list & studied_today is True",
        sc == 200 and sc_s == 200 and has_test_session and studied_now is True,
        f"in_list: {has_test_session}, studied_today: {studied_now}",
    )

    # --- 7. GET /api/stats/weekly ---
    print("\n[STEP 7/13] Checking /api/stats/weekly ...")
    sc, _, weekly_data, _ = request(f"{base_url}/api/stats/weekly")
    check(
        "GET /api/stats/weekly returns subjects & total minutes",
        sc == 200 and weekly_data and "total_minutes" in weekly_data and "subjects" in weekly_data,
        f"status: {sc}",
    )

    # --- 8. GET /api/goals/progress ---
    print("\n[STEP 8/13] Checking /api/goals/progress ...")
    sc, _, goals_data, _ = request(f"{base_url}/api/goals/progress")
    check(
        "GET /api/goals/progress returns daily/weekly blocks",
        sc == 200 and goals_data and "daily" in goals_data and "weekly" in goals_data,
        f"status: {sc}",
    )

    # --- 9. GET /api/export.csv ---
    print("\n[STEP 9/13] Checking /api/export.csv ...")
    sc, csv_text, _, hdrs = request(f"{base_url}/api/export.csv")
    check(
        "GET /api/export.csv returns CSV header row",
        sc == 200 and "id,date,subject,duration_minutes,notes,created_at" in csv_text,
        f"status: {sc}",
    )

    # --- 10. GET /api/insights/forecast ---
    print("\n[STEP 10/13] Checking /api/insights/forecast ...")
    sc, _, fc_data, _ = request(f"{base_url}/api/insights/forecast")
    check(
        "GET /api/insights/forecast returns 7-day forecast",
        sc == 200 and fc_data and len(fc_data.get("days", [])) == 7 and "weekly_total" in fc_data,
        f"status: {sc}",
    )

    # --- 11. GET /api/insights/streak-risk ---
    print("\n[STEP 11/13] Checking /api/insights/streak-risk ...")
    sc, _, risk_data, _ = request(f"{base_url}/api/insights/streak-risk")
    check(
        "GET /api/insights/streak-risk returns probability & factors",
        sc == 200
        and risk_data
        and "probability_study_tomorrow" in risk_data
        and "risk_level" in risk_data,
        f"status: {sc}",
    )

    # --- 12. GET /api/insights/recommendations ---
    print("\n[STEP 12/13] Checking /api/insights/recommendations ...")
    sc, _, recs_data, _ = request(f"{base_url}/api/insights/recommendations")
    check(
        "GET /api/insights/recommendations returns list",
        sc == 200 and recs_data and "recommendations" in recs_data,
        f"status: {sc}",
    )

    # --- 13. DELETE /api/sessions/{id} ---
    if session_id:
        print(f"\n[STEP 13/13] Cleaning up test session id {session_id} ...")
        sc, _, _, _ = request(f"{base_url}/api/sessions/{session_id}", method="DELETE")
        check("DELETE /api/sessions/{id} returns 204", sc == 204, f"status: {sc}")
    else:
        print("\n[STEP 13/13] Skipping cleanup (no session created).")

    print("\n" + "=" * 70)
    if all_passed:
        print("  ALL 13 SMOKE TEST CHECKS PASSED SUCCESSFULLY! [OK]")
    else:
        print("  SOME SMOKE TEST CHECKS FAILED! [FAIL]")
    print("=" * 70 + "\n")
    return all_passed


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    success = run_smoke_test(target)
    sys.exit(0 if success else 1)
