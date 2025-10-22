### **Project Overview: "Immo-Scraper-Hub" / General Scrapper: NocoDB Scrapper**

A secure, multi-user web application that allows authorized users to automatically scrape apartment listing data from various real estate websites and populate it into a shared NocoDB database. The system will be highly configurable via JSON files for easy maintenance and expansion. Python and web app should be defined through config file cause this tool should be general scrapper cause the same logic and interface could be executed on mulitple occasions. therefore in the config.json set the title and description as well as a small config json for the frontend which its load all variables and title texts. This general tool is called NocoDB Web Scrapper (this is also the github name of my project). Create also in each phase full Readme with features and small documentation to setup and also change strucutre of mapping.

---

### **Core Architecture**

*   **Frontend:** A single-page Vanilla JavaScript/HTML/CSS application. It handles user authentication and provides the interface for submitting URLs.
*   **Backend:** A Python FastAPI server. It manages user accounts, orchestrates the web scraping, and communicates with the NocoDB API.
*   **Data Storage:** A set of JSON files on the server for configuration, user credentials, and mappings. NocoDB is the primary database for the scraped apartment data.
*   **Security:** The FastAPI server is the single point of entry. It authenticates users with JWT and securely stores a master NocoDB API token, which is never exposed to the client. The entire application will run behind your existing Nginx reverse proxy with SSL.

---

### **Phase 1: Backend Foundation & Core Scraping (MVP)**

**Goal:** Create a functional backend that can accept a URL from an authenticated (hardcoded) user, scrape it based on a config file, and add it to NocoDB. This phase focuses entirely on the server-side logic and can be tested via API tools like Postman or `curl`.

#### **1. File & Folder Structure (Backend)**

```
/immo-scraper-hub
|
|-- backend/
|   |-- venv/               # Virtual environment
|   |-- main.py             # FastAPI app: routes for auth, scraping, user management
|   |-- scraper.py          # All web scraping logic (using Playwright/BeautifulSoup)
|   |-- auth.py             # Authentication logic (hashing, JWT creation/verification)
|   |-- config.py           # Pydantic models for loading and validating configs
|   |-- data/
|   |   |-- config.json     # Main app settings (signup password, secrets)
|   |   |-- login.json      # Stores user credentials {username: hashed_password}
|   |   |-- user_map.json   # Maps app usernames to NocoDB email addresses
|   |   |-- scrapers.json   # Scraper definitions for each website
|   |
|   |-- .env                # For secret keys (NocoDB token, JWT secret)
|   |-- requirements.txt    # Python dependencies
|
|-- frontend/
    |-- (To be created in Phase 2)
```

#### **2. Detailed Logic & Instructions**

**A. JSON Configuration Files (`/data/*.json`)**

*   **`.env` File:**
    *   `NOCODB_API_TOKEN`: Your secret NocoDB master token.
    *   `JWT_SECRET_KEY`: A long, random string for signing JWTs.
    *   `ALGORITHM`: "HS256"

*   **`data/config.json`:**
    ```json
    {
      "app_name": "Immo-Scraper-Hub",
      "signup_secret": "a-very-secret-password-for-friends"
    }
    ```

*   **`data/login.json`:** (Start with one user for testing)
    ```json
    {
      "admin": "$2b$12$....hashedpasswordhere...."
    }
    ```

*   **`data/user_map.json`:**
    ```json
    {
      "admin": "admin.user@nocodb-email.com"
    }
    ```

*   **`data/scrapers.json`:** (The core of the dynamic scraper)
    ```json
    {
      "www.immoscout24.de": {
        "nocodb_field_map": {
          "Title": "title",
          "Warmmiete": "warm_rent",
          "Kaution": "deposit",
          "Area_m2": "area"
        },
        "selectors": {
          "title": {"type": "id", "value": "expose-title"},
          "warm_rent": {"type": "css", "value": ".is24-sc-sub-headline.is24-sc-sub-headline-m.is24-sc-sub-headline-regular.is24-sc-sub-headline-warm"},
          "deposit": {"type": "class", "value": "is24-key-value-pair__value--72v17"},
          "area": {"type": "class", "value": "is24-key-value-pair__value--72v17"}
        }
      },
      "www.immowelt.de": {
        "nocodb_field_map": { ... },
        "selectors": { ... }
      }
    }
    ```
    *   **`nocodb_field_map`**: Maps the NocoDB column name (key) to the internal name used in `selectors` (value).
    *   **`selectors`**: A dictionary where each key is an internal name for a piece of data. The value is an object specifying the `type` of selector (`id`, `class`, `css`, `xpath`) and its `value`. This design is highly extensible.

**B. Backend Logic (`.py` files)**

*   **`auth.py`:**
    *   Use `passlib` for password hashing and verification.
    *   Functions: `verify_password()`, `get_password_hash()`.
    *   Use `python-jose` for JWTs.
    *   Functions: `create_access_token()`, a dependency `get_current_user()` that cracks the token from the request header and returns the username.

*   **`scraper.py`:**
    *   Create a main function: `scrape_apartment_data(url: str, config: dict) -> dict`.
    *   Inside, use `playwright` to get the page's HTML content.
    *   Use `BeautifulSoup` to parse the HTML.
    *   Loop through the `config['selectors']` dictionary. For each piece of data (e.g., "title", "warm_rent"):
        *   Use a `match/case` or `if/elif` block on `selector['type']`.
        *   Call the appropriate BeautifulSoup method (`find(id=...)`, `select_one(...)`, etc.).
        *   Extract the text, clean it up (remove "€", whitespace), and convert to a number if necessary.
        *   Store the results in a dictionary.
    *   Return the dictionary of scraped data.

*   **`main.py`:**
    *   On startup, load all JSON files and the `.env` file.
    *   **Route `POST /token`:** The login route. Takes username/password, verifies them against `login.json` using `auth.py`, and returns a JWT.
    *   **Route `POST /scrape`:**
        1.  This route will be protected by the `Depends(get_current_user)` dependency.
        2.  It accepts a request body with a `url`.
        3.  Parse the domain from the URL (`urllib.parse`).
        4.  Look up the domain in the `scrapers.json` config. If not found, return an error.
        5.  Call `scraper.scrape_apartment_data()` with the URL and the retrieved config.
        6.  Take the resulting data dict and map its keys to NocoDB field names using the `nocodb_field_map`.
        7.  Look up the current user's email in `user_map.json`.
        8.  Add the `URL` and `CreatedBy` (formatted as `[{"email": ...}]`) fields to the final data payload.
        9.  Make a `POST` request to the NocoDB API with the master token and the final payload.
        10. Return a success or failure response.

---

### **Phase 2: Frontend UI & User Self-Service**

**Goal:** Build the user-facing web interface and all remaining authentication and user management routes on the backend.

#### **1. File & Folder Structure (Frontend)**

```
/immo-scraper-hub
|
|-- backend/
|   |-- (As above)
|
|-- frontend/
    |-- index.html
    |-- js/
    |   |-- app.js
    |-- css/
    |   |-- style.css
```

#### **2. Detailed Logic & Instructions**

**A. Backend Additions (`main.py`)**

*   **Route `POST /signup`:**
    *   Accepts `username`, `password`, `nocodb_email`, and the `signup_secret`.
    *   Validate that the `signup_secret` matches the one in `config.json`.
    *   Check if the username already exists in `login.json`.
    *   Hash the new password.
    *   Atomically read, update, and write to both `login.json` and `user_map.json`.
    *   Return a success message.

*   **Route `PUT /users/me`:**
    *   Protected route `Depends(get_current_user)`.
    *   Accepts `new_password` (optional) and/or `nocodb_email` (optional).
    *   If `new_password` is provided, hash it and update the user's entry in `login.json`.
    *   If `nocodb_email` is provided, update the user's entry in `user_map.json`.
    *   Return a success message.

*   **Static File Serving:** Configure FastAPI to serve the `frontend` directory.

**B. Frontend Logic**

*   **`index.html`:**
    *   A container div for the entire app.
    *   A `<div id="login-view">` with the login form and a link to the signup form.
    *   A `<div id="signup-view">` (initially hidden) with the signup form (including the secret password field).
    *   A `<div id="main-view">` (initially hidden) containing:
        *   A header: `<h1 id="welcome-header">Welcome!</h1>`
        *   Status indicators: `<span id="api-status"></span>`, `<span id="nocodb-status"></span>`
        *   The URL input form: `<input id="url-input">`, `<button id="scrape-button">`
        *   A notice area: `<div id="notice-area"></div>`
        *   A settings section: `<div id="settings-area">` with forms for changing password and NocoDB email.

*   **`js/app.js`:**
    *   On `DOMContentLoaded`, check `localStorage` for a JWT. If valid, show `main-view`; otherwise, show `login-view`.
    *   **Login Function:** Add event listener to login form. On submit, call the `POST /token` endpoint. On success, store the JWT in `localStorage`, update the UI to show `main-view`, and set the welcome header.
    *   **Scrape Function:** Add event listener to scrape button. On click, show a "Processing..." message. Call the `POST /scrape` endpoint with the URL and the JWT in the `Authorization: Bearer <token>` header. Update the notice area with the result.
    *   **Settings Functions:** Add listeners to the settings forms to call the `PUT /users/me` endpoint.
    *   **UI Logic:** Functions to toggle visibility of views, update the notice area with styled success/error messages, etc.

---

### **Phase 3: Refinements & Advanced Features**

**Goal:** Polish the application, making it more robust and user-friendly. And fully Generalized with all namespaces and variables editable so its not only a immo scrapper but also for what ever websites and infos you want.

#### **Detailed Logic & Instructions**

*   **Backend (`main.py`)**:
    *   **Route `GET /status`:** A public route that checks its own status and attempts a simple `GET` request to the NocoDB API (e.g., fetch one row) to verify the connection and token. The frontend can periodically call this to update the status indicators.
    *   **Route `POST /validate-email`:** A protected route that takes an email and uses the NocoDB API's user endpoints (`/api/v1/db/meta/users`) to check if a user with that email actually exists. This provides real-time feedback in the settings area.
    *   **Better Error Handling:** Refine the `/scrape` endpoint to return more specific errors (e.g., "Domain not supported," "Scraping failed: Could not find 'warm_rent' selector," "NocoDB API rejected the request").

*   **Frontend (`js/app.js`)**:
    *   Implement the periodic calls to `/status`.
    *   Add a real-time check when the user is typing in the "change NocoDB email" field by calling `/validate-email`.
    *   Improve the notice area to display detailed errors returned from the backend.

*   **Scraping (`scrapers.json` & `scraper.py`)**:
    *   Add more robust selectors. For values like rent and area that appear multiple times, use more specific CSS selectors to pinpoint the exact one (e.g., `div.price-info > span.value`).
    *   Add post-processing steps. For example, a field in the scraper config could define a regex to apply to the extracted text to clean it reliably.