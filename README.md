# NocoDB Web Scraper

A secure, multi-user web application that allows authorized users to automatically scrape data from various websites and populate it into a shared NocoDB database. The system is highly configurable via JSON files for easy maintenance and expansion.

## 🎯 **Current Status: Phase 3 Enhanced ✅**

The application now includes advanced security features, dynamic field configuration, enhanced duplicate checking, and improved user experience with robust data handling.

## ✨ **Features**

### 🔐 **Enhanced Security**
- JWT-based authentication with automatic token refresh
- User registration with secret key validation
- **NEW**: Authentication checks on all sensitive operations
- **NEW**: Complete data cleanup on logout
- **NEW**: Prevention of unauthorized access to UI components
- Secure session management and timeout handling
- Multi-user support with individual NocoDB email mapping

### 🕷️ **Advanced Web Scraping**
- Playwright-based scraping for modern JavaScript websites
- **NEW**: Dynamic field configuration with types (map, input_url, nocodb_email)
- **NEW**: Enhanced URL cleaning and normalization
- Configurable selectors (id, class, css, xpath)
- Automatic data cleaning and number conversion
- Fallback to manual input when scraping fails

### 🔄 **Robust Duplicate Prevention**
- **NEW**: Enhanced duplicate checking in both check-url and save-data endpoints
- **NEW**: Configurable duplicate check fields per scraper
- **NEW**: URL cleaning to prevent duplicate detection issues
- Real-time duplicate detection before data entry

### 🎨 **Modern Frontend Interface**
- Responsive design for all devices
- **NEW**: Improved URL input layout with full-width input field
- Dynamic form generation from configuration
- Real-time status monitoring
- **NEW**: Null-safe error handling and user feedback
- Intuitive user experience with smooth animations

### ⚙️ **Highly Configurable**
- **NEW**: Dynamic field types and behaviors in scrapers.json
- JSON-based configuration for websites and forms
- Dynamic field validation and types
- Theme customization
- Multi-language support structure

### 🛡️ **Security Features**
- Server-side validation for all inputs
- **NEW**: Enhanced duplicate URL detection with cleaned URLs
- Secure password hashing with Argon2
- No sensitive data exposure to frontend
- **NEW**: Forced authentication for all protected routes

## 🏗️ **Architecture**

```
NocoDB_Web_Scrapper/
├── backend/                    # FastAPI Python backend
│   ├── main.py                # API server with all endpoints
│   ├── auth.py                # JWT authentication
│   ├── config.py              # Configuration management
│   ├── scraper.py             # Web scraping logic
│   ├── requirements.txt       # Python dependencies
│   └── data/                  # Configuration files
│       ├── config.json        # App settings
│       ├── login.json         # User credentials
│       ├── user_map.json      # Email mappings
│       ├── scrapers.json      # Website configurations
│       └── ux.json            # UI form configuration
├── frontend/                   # Modern web interface
│   ├── index.html             # Main HTML structure
│   ├── css/style.css          # Complete styling
│   └── js/app.js              # Application logic
├── Plan.md                    # Original project plan
├── README.md                  # This file
└── PHASE2_README.md           # Phase 2 documentation
```

## 🚀 **Quick Start**

### Prerequisites
- Python 3.8+
- NocoDB instance with API access
- Modern web browser

### Installation

1. **Navigate to backend directory:**
   ```bash
   cd NocoDB_Web_Scrapper/backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers:**
   ```bash
   playwright install
   ```

5. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your NocoDB credentials
   ```

6. **Start the server:**
   ```bash
   python main.py
   ```

7. **Access the application:**
   - Frontend: Serve `frontend/` directory with your web server (nginx, apache, etc.)
   - API: `http://localhost:8000`
   - API Docs: `http://localhost:8000/docs`

### Alternative: Deploy with Docker Compose

```bash
# Navigate to docker directory
cd docker

# Make deploy script executable
chmod +x docker_setup.sh

# Run deployment
./docker_setup.sh
```

### Default Credentials
- **Username**: `admin`
- **Password**: `admin123`

## 📖 **Usage Guide**

### 1. **User Registration**
1. Click "Registrieren" on the login page
2. Enter username, NocoDB email, and password
3. Provide the signup secret (configured in backend)
4. Login with your new credentials

### 2. **Scraping Workflow**
1. **Enter URL**: Paste the listing URL in the input field
2. **Select Mode**: Choose "Automatisch scrapen" or "Manuell eingeben"
3. **Check URL**: Click "URL prüfen" to validate and check for duplicates
4. **Edit Data**: Review and edit the extracted data in the dynamic form
5. **Save**: Click "Speichern" to save to NocoDB

### 3. **Settings Management**
1. Click your username in the top-right corner
2. Select "Einstellungen"
3. Update your NocoDB email or password
4. Save changes

## 🔧 **Configuration**

### NocoDB Setup
1. **Get API Token**: Account Settings → API Tokens in NocoDB
2. **Get IDs**: From URL `/nc/project_id/table_id`
3. **Get Field IDs**: Hover over fields in NocoDB table

### Update Configuration Files

**scrapers.json** - Dynamic field configuration with types:
```json
{
  "www.immobilienscout24.de": {
    "nocodb_field_map": {
      "title": {"id": "your-title-field-id", "type": "map"},
      "warm_rent": {"id": "your-rent-field-id", "type": "map"},
      "url_address": {"id": "your-url-field-id", "type": "input_url", "duplicate_check": true},
      "found_by": {"id": "your-user-field-id", "type": "nocodb_email"},
      "in_charge": {"id": "your-charge-field-id", "type": "nocodb_email"}
    },
    "selectors": {
      "title": {"type": "id", "value": "expose-title"},
      "warm_rent": {"type": "css", "value": "div.is24qa-warmmiete .is24-value"}
    },
    "url_cleaning": {
      "extract_pattern": "https://www\\.immobilienscout24\\.de/expose/(\\d+)",
      "clean_pattern": "https://www.immobilienscout24.de/expose/{id}"
    }
  }
}
```

**Field Types:**
- `map` - Maps scraped data to NocoDB field
- `input_url` - Uses cleaned URL for this field
- `nocodb_email` - Uses current user's NocoDB email
- `duplicate_check: true` - Enables duplicate checking for this field

**user_map.json** - Update email mapping:
```json
{
  "admin": "your-nocodb-email@example.com"
}
```

**ux.json** - Customize form fields and UI

## 🎯 **Supported Websites**

### Currently Configured:
- **Immobilienscout24.de** - German real estate listings
- **Immowelt.de** - German real estate listings

### Adding New Websites:
1. Add configuration to `scrapers.json`
2. Define field mappings and selectors
3. Test with the `/check-url` endpoint

## 🔌 **API Endpoints**

### Authentication
- `POST /token` - User login
- `POST /signup` - User registration
- `PUT /users/me` - Update user settings

### Scraping
- `GET /ux-config` - Get UI configuration
- `POST /check-url` - Validate URL and check duplicates
- `POST /save-data` - Save data to NocoDB
- `GET /status` - System status

### Legacy
- `POST /scrape` - Direct scraping (Phase 1)

## 🛡️ **Security Features**

- **JWT Authentication**: Secure token-based authentication
- **Input Validation**: Client and server-side validation
- **Duplicate Prevention**: URL checking before saving
- **Secure Headers**: CORS and security headers
- **Password Hashing**: bcrypt password hashing
- **Session Management**: Automatic token refresh

## 📱 **Responsive Design**

- **Mobile**: Optimized for mobile devices
- **Tablet**: Adaptive layouts for tablets
- **Desktop**: Full-featured desktop experience
- **Touch-friendly**: Appropriate touch targets

## 🔍 **Troubleshooting**

### Common Issues

1. **Login fails**: Check backend is running and credentials are correct
2. **Scraping fails**: Website may have bot protection, use manual mode
3. **Save fails**: Verify NocoDB field mappings and permissions
4. **Status offline**: Check NocoDB connection and API token

### Debug Mode
Enable browser console debugging:
```javascript
localStorage.setItem('debug', 'true');
```

## 📊 **System Status**

The application includes real-time status monitoring:
- **API Status**: Backend service health
- **NocoDB Status**: Database connection status
- **Automatic Updates**: Status refreshes every 30 seconds

## 🔄 **Data Flow**

```
1. User enters URL → Frontend validation
2. URL check request → Backend validation
3. Scraping (if enabled) → Data extraction
4. Form generation → Dynamic UI
5. User editing → Data validation
6. Save request → NocoDB storage
7. Success feedback → User notification
```

## 🎨 **Customization**

### Theme Customization
Edit CSS variables in `style.css`:
```css
:root {
    --primary-color: #2563eb;
    --success-color: #16a34a;
    --warning-color: #f59e0b;
    --error-color: #dc2626;
}
```

### Form Field Types
- `text` - Standard text input
- `number` - Numeric input with validation
- `currency` - Currency formatting
- `select` - Dropdown selection
- `email` - Email validation

## 📈 **Performance**

- **Lazy Loading**: Components loaded as needed
- **Efficient API**: Optimized database queries
- **Caching**: Configuration caching
- **Minimized Requests**: Batch operations where possible

## 🔮 **Recent Phase 3 Enhancements**

### ✅ **Completed Features:**
- **Dynamic Field Configuration**: Types-based field mapping (map, input_url, nocodb_email)
- **Enhanced Security**: Authentication checks on all sensitive operations
- **Robust Duplicate Prevention**: Multi-level duplicate checking with URL cleaning
- **Improved UX**: Full-width URL input and better form layouts
- **Data Cleanup**: Complete data sanitization on logout
- **Error Handling**: Null-safe operations and better user feedback
- **Port Configuration**: Backend now runs on port 8000 for standardization, docker on 8091
- **Docker Support**: Alternative deployment method with Docker Compose

### 🔧 **Technical Improvements:**
- Enhanced URL cleaning and normalization
- Configurable duplicate check fields per scraper
- Better error messages and debugging information
- Improved frontend security with forced authentication
- Enhanced form validation and null-checking

## 📈 **Performance & Security**

- **Enhanced Security**: Argon2 password hashing, authentication guards
- **Improved Reliability**: Better error handling and duplicate prevention
- **User Experience**: Cleaner interfaces and more intuitive workflows
- **Data Integrity**: Multi-level validation and cleaning processes

## 📄 **License**

This project is open source. Please refer to the license file for details.

## 🤝 **Support**

For issues and questions:
1. Check the troubleshooting section
2. Review the API documentation
3. Create an issue in the project repository

---

**🎉 Phase 3 Enhanced Complete!** The NocoDB Web Scraper now provides a production-ready solution with advanced security, dynamic configuration, robust duplicate prevention, and enhanced user experience. The system is more reliable, secure, and user-friendly than ever before.