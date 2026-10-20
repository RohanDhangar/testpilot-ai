import asyncio
from app.services.code_validation import repaire_generated_code
code: str = "import asyncio\nimport os\nimport re\nfrom playwright.async_api import async_playwright, expect\n\n\nasync def test_login():\n    username = os.environ.get(\"TEST_USERNAME\")\n    password = os.environ.get(\"TEST_PASSWORD\")\n\n    if not username or not password:\n        raise ValueError(\"TEST_USERNAME and TEST_PASSWORD environment variables must be set.\")\n\n    async with async_playwright() as p:\n        browser = await p.chromium.launch(headless=True)\n        page = await browser.new_page()\n\n        # Step 1: Navigate to the login page\n        await page.goto(\"https://qk.peoplestrong.com/\")\n\n        # Step 3: Enter the username\n        # In the accessibility snapshot, the first textbox corresponds to the UserName field\n   username_field = page.get_by_role(\"textbox\").first\n        await username_field.fill(username)\n\n        # Step 4: Enter the password\n        # In the accessibility snapshot, the second textbox corresponds to the Password field\n        password_field = page.get_by_role(\"textbox\").nth(1)\nawait password_field.fill(password)\n\n        # Step 5: Click the Continue button\n        continue_button = page.get_by_role(\"button\", name=\"Continue\")\n        await continue_button.click()\n\n        # Step 6: Verify navigation/redirection away from the login page\n        await expect(page).not_to_have_url(re.compile(r\".*altLogin\\.jsf.*$\"), timeout=15000)\n\n        await browser.close()\n\n\nif __name__ == \"__main__\":\n    asyncio.run(test_login())\n";

# format_code = json.loads(json.dumps({"code": code, "language": "python", "framework": "playwright", "test_type": "login"}))

async def code_check(code: str):
    repaired_code = await repaire_generated_code(code)
    if repaired_code.get("status") != "success":
        print("""ss"status": "error", "message": "Generated code could not pass syntax validation.","validation": repaired_code.get("validation"),""")
        return
    
    print(repaired_code.get("test_code"))

if __name__ == "__main__":
    asyncio.run(code_check(code))