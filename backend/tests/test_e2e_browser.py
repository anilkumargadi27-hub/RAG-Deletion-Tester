import threading
import time
import uvicorn
import pytest
from playwright.sync_api import sync_playwright

from backend.app.main import app

PORT = 8011

@pytest.fixture(scope="module")
def live_server():
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1.5)
    yield f"http://127.0.0.1:{PORT}"
    server.should_exit = True
    thread.join(timeout=2)

def test_full_browser_walkthrough(live_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Login Page
        page.goto(f"{live_server}/login")
        page.wait_for_selector("text=ForgetCheck")
        assert "ForgetCheck" in page.content()

        # Login as Admin
        page.fill('input[placeholder="Enter username"]', "admin")
        page.fill('input[placeholder="••••••••••••"]', "Admin@ForgetCheck2026!")
        page.click('button[type="submit"]')

        # 2. Overview Dashboard
        page.wait_for_url(f"{live_server}/", timeout=6000)
        page.wait_for_selector("text=Check what your AI can still reveal after access changes.")
        assert "Overview" in page.content()

        # 3. Documents Page: Ingest Document via UI
        page.goto(f"{live_server}/documents")
        page.wait_for_selector("text=Documents & Access Control")

        # Open paste modal and submit document
        page.click("text=Paste Text Document")
        page.wait_for_selector('input[placeholder="e.g. Q4 Executive Bonus Schedule"]')
        page.fill('input[placeholder="e.g. Q4 Executive Bonus Schedule"]', "Corporate Health Benefits 2026")
        page.fill('textarea[placeholder="Enter document text..."]', "All full-time employees are provided CarePlus Platinum health insurance coverage.")
        page.click("text=Index Document")

        # Verify document appears in table
        page.wait_for_selector("text=Corporate Health Benefits 2026", timeout=8000)
        assert "Corporate Health Benefits 2026" in page.content()

        # 4. Assistant Playground: Ask question and receive cited answer
        page.goto(f"{live_server}/playground")
        page.wait_for_selector("text=Assistant Grounded Playground")
        page.fill('input[placeholder="Ask a question about company documents..."]', "What health insurance covers employees?")
        page.click('button[type="submit"]')

        # Wait for cited response
        page.wait_for_selector("text=CarePlus", timeout=10000)
        assert "CarePlus" in page.content()

        # 5. Guided Demo Execution
        page.goto(f"{live_server}/demo")
        page.wait_for_selector("text=Guided Verification Demo")
        page.click("text=Start Step-by-Step Execution")

        # Wait for faulty leak detection
        page.wait_for_selector("text=Leak Detected: AI Disclosed Deleted Secret", timeout=15000)
        assert "CANARY-HR-78923-SAL" in page.content() or "90,000" in page.content()

        # Rerun with corrected secure pipeline
        page.click("text=Rerun with Corrected Secure Pipeline")

        # Wait for secure verification to pass
        page.wait_for_selector("text=Secure Verification Passed: No Leakage Observed", timeout=15000)
        assert "No Leakage Observed" in page.content()

        # 6. Reports Page
        page.goto(f"{live_server}/reports")
        page.wait_for_selector("text=Audit Reports & Exports")
        assert "Completed Test Audits" in page.content()

        browser.close()
