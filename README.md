# TestPilot AI

TestPilot AI is an AI-powered test automation platform that converts testing requirements written in plain English into Playwright test code.

Users provide a web application URL and describe what they want to test. The application uses Google Gemini to understand the requirement and generate test code, while Playwright MCP helps inspect the target application. The generated Python code is checked for syntax errors before being returned to the user.

The frontend is built with React, and the backend uses Python and FastAPI.

## Tech Stack

- Python and FastAPI
- Google Gemini API
- Playwright MCP
- Playwright
- React.js and Vite
- JavaScript and CSS

## Current Features

- Generate Playwright test code from natural language requirements.
- Inspect web applications to understand their pages and elements.
- Validate generated code for Python syntax errors.
- Display and copy the generated code from the frontend.

**Note:** The platform currently generates and validates test code but does not execute the generated tests automatically.
