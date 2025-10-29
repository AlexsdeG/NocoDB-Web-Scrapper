// NocoDB Web Scraper Frontend Application
class WebScraperApp {
    constructor() {
        this.apiBase = `${window.location.origin}/api`;
        this.currentUser = null;
        this.uxConfig = null;
        this.currentUrl = null;
        this.currentMode = null;
        this.scrapedData = null;
        this.tokenRefreshTimer = null;
        
        this.init();
    }

    async init() {
        this.bindEvents();
        await this.loadUXConfig();
        this.checkAuthStatus();
        
        // Start status polling status
        this.startStatusPolling();
    }
    
    isAuthenticated() {
        return this.currentUser && localStorage.getItem('access_token');
    }
    
    requireAuth() {
        if (!this.isAuthenticated()) {
            this.showNotice('Bitte melden Sie sich an, um fortzufahren', 'error');
            this.showView('login-view');
            return false;
        }
        return true;
    }

    // Event Binding
    bindEvents() {
        // Login/Signup
        document.getElementById('login-form').addEventListener('submit', (e) => this.handleLogin(e));
        document.getElementById('signup-form').addEventListener('submit', (e) => this.handleSignup(e));
        document.getElementById('show-signup-btn').addEventListener('click', () => this.showView('signup-view'));
        document.getElementById('show-login-btn').addEventListener('click', () => this.showView('login-view'));

        // User Menu
        document.getElementById('user-menu-btn').addEventListener('click', () => this.toggleUserDropdown());
        document.getElementById('settings-btn').addEventListener('click', () => this.showSettings());
        document.getElementById('logout-btn').addEventListener('click', () => this.handleLogout());

        // Main Interface
        document.getElementById('url-form').addEventListener('submit', (e) => this.handleURLCheck(e));
        document.getElementById('back-btn').addEventListener('click', () => this.backToURLInput());
        document.getElementById('save-btn').addEventListener('click', () => this.handleSave());

        // Settings
        document.getElementById('settings-back-btn').addEventListener('click', () => this.backToMain());
        document.getElementById('user-settings-form').addEventListener('submit', (e) => this.handleSettingsUpdate(e));

        // Close dropdowns when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.user-menu')) {
                document.getElementById('user-dropdown').classList.remove('show');
            }
        });
    }

    // View Management
    showView(viewId) {
        document.querySelectorAll('.view').forEach(view => view.classList.add('hidden'));
        document.getElementById(viewId).classList.remove('hidden');
    }

    // API Configuration
    async loadUXConfig() {
        try {
            const response = await this.apiRequest('/ux-config');
            if (response.success) {
                this.uxConfig = response.config;
                this.updateUIFromConfig();
            }
        } catch (error) {
            console.error('Failed to load UX config:', error);
            // Don't show error on initial load if not authenticated
            if (this.isAuthenticated()) {
                this.showNotice('Fehler beim Laden der Konfiguration', 'error');
            }
        }
    }

    updateUIFromConfig() {
        if (!this.uxConfig) return;

        const config = this.uxConfig.frontend_config;
        document.getElementById('page-title').textContent = config.app_title;
        document.getElementById('app-title').textContent = config.app_title;
        document.getElementById('welcome-header').textContent = `Willkommen bei ${config.app_title}!`;
        document.getElementById('login-description').textContent = config.app_description;
        document.getElementById('signup-description').textContent = 'Neues Konto für den Web Scraper erstellen';
        document.getElementById('welcome-description').textContent = 'Geben Sie eine URL ein, um Daten zu extrahieren und in NocoDB zu speichern';

        // Update input mode options
        const modeSelect = document.getElementById('input-mode');
        modeSelect.innerHTML = '';
        this.uxConfig.input_modes.forEach(mode => {
            const option = document.createElement('option');
            option.value = mode.value;
            option.textContent = mode.label;
            modeSelect.appendChild(option);
        });
    }

    // Authentication
    async checkAuthStatus() {
        const token = localStorage.getItem('access_token');
        if (token) {
            try {
                // Verify token by making a protected request
                await this.apiRequest('/status');
                this.currentUser = this.getUsernameFromToken();
                // Reload UX config if not loaded
                if (!this.uxConfig) {
                    await this.loadUXConfig();
                }
                this.showMainInterface();
            } catch (error) {
                localStorage.removeItem('access_token');
                this.showView('login-view');
            }
        } else {
            this.showView('login-view');
        }
    }

    getUsernameFromToken() {
        const token = localStorage.getItem('access_token');
        if (!token) return null;

        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            return payload.sub;
        } catch (error) {
            return null;
        }
    }

    async handleLogin(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        
        this.showLoading('Anmeldung läuft...');
        
        try {
            const response = await this.apiRequest('/token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams(formData)
            });

            localStorage.setItem('access_token', response.access_token);
            this.currentUser = formData.get('username');
            
            // Reload UX config after login
            await this.loadUXConfig();
            
            this.showMainInterface();
            this.showNotice('Erfolgreich angemeldet!', 'success');
        } catch (error) {
            this.showNotice('Anmeldung fehlgeschlagen: ' + error.message, 'error');
        } finally {
            this.hideLoading();
        }
    }

    async handleSignup(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData);
        
        this.showLoading('Registrierung läuft...');
        
        try {
            const response = await this.apiRequest('/signup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            this.showNotice('Registrierung erfolgreich! Sie können sich jetzt anmelden.', 'success');
            this.showView('login-view');
            e.target.reset();
        } catch (error) {
            this.showNotice('Registrierung fehlgeschlagen: ' + error.message, 'error');
        } finally {
            this.hideLoading();
        }
    }

    handleLogout() {
        // Clear authentication data
        localStorage.removeItem('access_token');
        this.currentUser = null;
        document.getElementById('username-display').textContent = 'Benutzer'
        
        // Clear all application data
        this.currentUrl = null;
        this.currentMode = null;
        this.scrapedData = null;
        // Don't clear uxConfig - keep it for UI consistency
        // this.uxConfig = null;
        
        // Clear all form inputs
        this.clearAllFormInputs();
        
        // Stop any ongoing processes
        if (this.tokenRefreshTimer) {
            clearInterval(this.tokenRefreshTimer);
            this.tokenRefreshTimer = null;
        }
        
        // Hide loading states
        this.hideLoading();
        
        // Show login view
        this.showView('login-view');
        this.showNotice('Erfolgreich abgemeldet!', 'info');
    }
    
    clearAllFormInputs() {
        // Clear URL input
        const urlInput = document.getElementById('url-input');
        if (urlInput) urlInput.value = '';
        
        // Clear login form
        const loginUsername = document.getElementById('login-username');
        const loginPassword = document.getElementById('login-password');
        if (loginUsername) loginUsername.value = '';
        if (loginPassword) loginPassword.value = '';
        
        // Clear signup form
        const signupUsername = document.getElementById('signup-username');
        const signupPassword = document.getElementById('signup-password');
        const signupRepassword = document.getElementById('signup-repassword');
        const signupEmail = document.getElementById('signup-email');
        const signupSecret = document.getElementById('signup-secret');
        if (signupUsername) signupUsername.value = '';
        if (signupPassword) signupPassword.value = '';
        if (signupRepassword) signupRepassword.value = '';
        if (signupEmail) signupEmail.value = '';
        if (signupSecret) signupSecret.value = '';
        
        // Clear settings form
        const settingsEmail = document.getElementById('settings-email');
        const settingsPassword = document.getElementById('settings-password');
        const settingsNewPassword = document.getElementById('settings-new-password');
        if (settingsEmail) settingsEmail.value = '';
        if (settingsPassword) settingsPassword.value = '';
        if (settingsNewPassword) settingsNewPassword.value = '';
        
        // Clear edit form if it exists
        const editForm = document.getElementById('edit-form');
        if (editForm) {
            const inputs = editForm.querySelectorAll('input, textarea, select');
            inputs.forEach(input => {
                if (input.type === 'checkbox' || input.type === 'radio') {
                    input.checked = false;
                } else {
                    input.value = '';
                }
            });
        }
    }

    showMainInterface() {
        document.getElementById('username-display').textContent = this.currentUser;
        document.getElementById('settings-username').value = this.currentUser;
        this.showView('main-view');
        this.startTokenRefresh();
    }

    // Token Management
    startTokenRefresh() {
        if (this.tokenRefreshTimer) {
            clearInterval(this.tokenRefreshTimer);
        }

        const threshold = this.uxConfig?.frontend_config?.token_refresh_threshold || 300;
        this.tokenRefreshTimer = setInterval(async () => {
            const token = localStorage.getItem('access_token');
            if (token) {
                try {
                    const payload = JSON.parse(atob(token.split('.')[1]));
                    const exp = payload.exp * 1000; // Convert to milliseconds
                    const now = Date.now();
                    
                    if (exp - now < threshold * 1000) {
                        await this.refreshToken();
                    }
                } catch (error) {
                    console.error('Token refresh error:', error);
                }
            }
        }, 60000); // Check every minute
    }

    async refreshToken() {
        // This would need a refresh token endpoint
        // For now, we'll just check if the token is still valid
        try {
            await this.apiRequest('/status');
        } catch (error) {
            this.handleLogout();
        }
    }

    // User Menu
    toggleUserDropdown() {
        if (!this.requireAuth()) return;
        
        const dropdown = document.getElementById('user-dropdown');
        if (dropdown) {
            dropdown.classList.toggle('show');
        }
    }

    showSettings() {
        if (!this.requireAuth()) return;
        
        const dropdown = document.getElementById('user-dropdown');
        if (dropdown) {
            dropdown.classList.remove('show');
        }
        this.loadUserSettings();
        this.showView('settings-view');
    }

    async loadUserSettings() {
        try {
            const userMap = await this.apiRequest('/users/me');
            // Set Username and NocoDB Email
            document.getElementById('settings-username').value = userMap.user.username;
            document.getElementById('settings-email').value = userMap.user.nocodb_email;
        } catch (error) {
            console.error('Failed to load user settings:', error);
        }
    }

    backToMain() {
        this.showView('main-view');
    }

    async handleSettingsUpdate(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData);
        
        // Get password confirmation field value (not in FormData if empty)
        const passwordConfirm = document.getElementById('settings-password-confirm');
        const passwordConfirmValue = passwordConfirm ? passwordConfirm.value : '';
        
        // Validate passwords match
        if (data.new_password && data.new_password !== passwordConfirmValue) {
            this.showNotice('Passwörter stimmen nicht überein', 'error');
            return;
        }

        // Remove password confirmation (it's not sent to backend)
        delete data.password_confirm;
        
        // Remove empty password
        if (!data.new_password) {
            delete data.new_password;
        }

        this.showLoading('Einstellungen werden gespeichert...');
        
        try {
            const response = await this.apiRequest('/users/me', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            this.showNotice('Einstellungen erfolgreich gespeichert!', 'success');
            
            // Reload user settings to show updated values
            await this.loadUserSettings();
            
            // Clear password fields only
            const newPasswordField = document.getElementById('settings-password');
            const confirmPasswordField = document.getElementById('settings-password-confirm');
            if (newPasswordField) newPasswordField.value = '';
            if (confirmPasswordField) confirmPasswordField.value = '';
            
        } catch (error) {
            this.showNotice('Fehler beim Speichern: ' + error.message, 'error');
        } finally {
            this.hideLoading();
        }
    }

    // Main Interface - URL Handling
    async handleURLCheck(e) {
        e.preventDefault();
        
        if (!this.requireAuth()) return;
        
        // Ensure UX config is loaded
        if (!this.uxConfig) {
            this.showLoading('Konfiguration wird geladen...');
            await this.loadUXConfig();
            this.hideLoading();
            
            if (!this.uxConfig) {
                this.showNotice('Fehler: Konfiguration konnte nicht geladen werden', 'error');
                return;
            }
        }
        
        const formData = new FormData(e.target);
        const url = formData.get('url');
        const mode = formData.get('mode');

        if (!this.isValidURL(url)) {
            this.showNotice('Bitte geben Sie eine gültige URL ein', 'error');
            return;
        }

        this.showLoading('URL wird geprüft...');
        
        try {
            const response = await this.apiRequest('/check-url', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url, mode })
            });

            if (response.success) {
                this.currentUrl = url;
                this.currentMode = mode;
                this.scrapedData = response.data.scraped_data;
                this.showEditForm();
            } else {
                this.showNotice(response.message, 'warning');
            }
        } catch (error) {
            this.showNotice('Fehler bei der URL-Prüfung: ' + error.message, 'error');
        } finally {
            this.hideLoading();
        }
    }

    isValidURL(string) {
        try {
            new URL(string);
            return true;
        } catch (_) {
            return false;
        }
    }

    // Edit Form
    showEditForm() {
        const formFields = document.getElementById('form-fields');
        if (!formFields) {
            this.showNotice('Formularfelder-Container nicht gefunden', 'error');
            return;
        }
        
        formFields.innerHTML = '';

        if (!this.uxConfig || !this.uxConfig.form_fields) {
            this.showNotice('Formularkonfiguration nicht gefunden', 'error');
            console.error('UX Config:', this.uxConfig);
            return;
        }

        this.uxConfig.form_fields.forEach(field => {
            const formGroup = this.createFormField(field);
            formFields.appendChild(formGroup);
        });

        // Populate with scraped data if available
        if (this.scrapedData) {
            this.populateFormWithScrapedData();
        }

        this.showView('main-view');
        
        const editSection = document.getElementById('edit-section');
        const urlSection = document.getElementById('url-section');
        
        if (editSection) {
            editSection.classList.remove('hidden');
        } else {
            console.error('Edit section not found');
        }
        
        if (urlSection) {
            urlSection.classList.add('hidden');
        } else {
            console.error('URL section not found');
        }
    }

    createFormField(fieldConfig) {
        const formGroup = document.createElement('div');
        formGroup.className = 'form-group';

        const label = document.createElement('label');
        label.setAttribute('for', `field-${fieldConfig.name}`);
        label.textContent = fieldConfig.label + (fieldConfig.required ? ' *' : '');
        formGroup.appendChild(label);

        let input;
        if (fieldConfig.type === 'select') {
            input = document.createElement('select');
            fieldConfig.options?.forEach(option => {
                const optionElement = document.createElement('option');
                optionElement.value = option.value;
                optionElement.textContent = option.label;
                input.appendChild(optionElement);
            });
        } else {
            input = document.createElement('input');
            input.type = this.getInputType(fieldConfig.type);
        }

        input.id = `field-${fieldConfig.name}`;
        input.name = fieldConfig.name;
        input.required = fieldConfig.required || false;
        input.placeholder = fieldConfig.placeholder || '';

        // Add validation
        if (fieldConfig.validation) {
            this.addValidation(input, fieldConfig.validation);
        }

        formGroup.appendChild(input);
        return formGroup;
    }

    getInputType(type) {
        const typeMap = {
            'text': 'text',
            'number': 'number',
            'currency': 'text',
            'email': 'email',
            'url': 'url'
        };
        return typeMap[type] || 'text';
    }

    addValidation(input, validation) {
        if (validation.min_length) input.minLength = validation.min_length;
        if (validation.max_length) input.maxLength = validation.max_length;
        if (validation.min !== undefined) input.min = validation.min;
        if (validation.max !== undefined) input.max = validation.max;
    }

    populateFormWithScrapedData() {
        Object.keys(this.scrapedData).forEach(key => {
            const input = document.getElementById(`field-${key}`);
            if (input && this.scrapedData[key] !== null) {
                input.value = this.scrapedData[key];
            }
        });
    }

    backToURLInput() {
        const editSection = document.getElementById('edit-section');
        const urlSection = document.getElementById('url-section');
        
        if (editSection) {
            editSection.classList.add('hidden');
        } else {
            console.error('Edit section not found');
        }
        
        if (urlSection) {
            urlSection.classList.remove('hidden');
        } else {
            console.error('URL section not found');
        }
        
        this.currentUrl = null;
        this.currentMode = null;
        this.scrapedData = null;
    }

    async handleSave() {
        const form = document.getElementById('edit-form');
        if (!form) {
            this.showNotice('Formular nicht gefunden', 'error');
            return;
        }

        const formData = new FormData(form);
        const data = {};
        
        // Process form data and convert types appropriately
        for (let [key, value] of formData.entries()) {
            // Skip empty values
            if (value === null || value === undefined || value.trim() === '') {
                continue;
            }
            data[key] = value;
        }

        // Validate required fields
        const missingFields = [];
        if (this.uxConfig && this.uxConfig.form_fields) {
            this.uxConfig.form_fields.forEach(field => {
                if (field.required && !data[field.name]) {
                    missingFields.push(field.label);
                }
            });
        }

        if (missingFields.length > 0) {
            this.showNotice(`Bitte füllen Sie die Pflichtfelder aus: ${missingFields.join(', ')}`, 'error');
            return;
        }

        // Convert currency and number fields
        if (this.uxConfig && this.uxConfig.form_fields) {
            this.uxConfig.form_fields.forEach(field => {
                if (data[field.name]) {
                    if (field.type === 'currency') {
                        // Convert currency to number
                        const parsedValue = this.parseCurrency(data[field.name]);
                        // Only set if we got a valid number
                        if (!isNaN(parsedValue) && parsedValue !== null && parsedValue !== '') {
                            data[field.name] = parsedValue;
                        } else {
                            // Remove invalid currency values
                            delete data[field.name];
                        }
                    } else if (field.type === 'number') {
                        // Convert to number
                        const parsedValue = parseFloat(data[field.name]);
                        if (!isNaN(parsedValue)) {
                            data[field.name] = parsedValue;
                        } else {
                            // Remove invalid number values
                            delete data[field.name];
                        }
                    }
                }
            });
        }

        this.showLoading('Daten werden gespeichert...');

        try {
            const response = await this.apiRequest('/save-data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url: this.currentUrl,
                    mode: this.currentMode,
                    data: data
                })
            });

            if (response.success) {
                this.showNotice('Daten erfolgreich in NocoDB gespeichert!', 'success');
                this.backToURLInput();
                // Clear the URL input
                document.getElementById('url-input').value = '';
            } else {
                this.showNotice(response.message, 'warning');
            }
        } catch (error) {
            this.showNotice('Fehler beim Speichern: ' + error.message, 'error');
        } finally {
            this.hideLoading();
        }
    }

    parseCurrency(value) {
        if (!value || value.trim() === '') {
            return null;
        }
        // Remove currency symbols and convert to number
        const cleaned = value.replace(/[€$£¥]/g, '').replace(/\s/g, '').replace(/\./g, '').replace(',', '.');
        const parsed = parseFloat(cleaned);
        return isNaN(parsed) ? null : parsed;
    }

    // Status Monitoring
    startStatusPolling() {
        const checkStatus = async () => {
            try {
                const response = await this.apiRequest('/status');
                this.updateStatusIndicators(response);
            } catch (error) {
                console.error('Status check failed:', error);
            }
        };
        checkStatus();
        setInterval(checkStatus, 60000); // Check every 60 seconds
    }

    updateStatusIndicators(statusData) {
        const apiStatus = document.getElementById('api-status');
        const nocodbStatus = document.getElementById('nocodb-status');

        // API Status
        apiStatus.className = 'status-indicator';
        if (statusData.api_status === 'running') {
            apiStatus.classList.add('online');
        } else {
            apiStatus.classList.add('offline');
        }

        // NocoDB Status
        nocodbStatus.className = 'status-indicator';
        if (statusData.nocodb_status === 'connected') {
            nocodbStatus.classList.add('online');
        } else {
            nocodbStatus.classList.add('offline');
        }
    }

    // API Helper
    async apiRequest(endpoint, options = {}) {
        // If Base url not set, throw error
        if (!this.apiBase) {
            throw new Error('API-Basis-URL ist nicht konfiguriert.');
        }

        const url = `${this.apiBase}${endpoint}`;
        const token = localStorage.getItem('access_token');

        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        if (token) {
            defaultOptions.headers.Authorization = `Bearer ${token}`;
        }

        const finalOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers,
            },
        };

        const response = await fetch(url, finalOptions);

        if (response.status === 401) {
            this.handleLogout();
            throw new Error('Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.');
        }

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    }

    // UI Helpers
    showLoading(text = 'Verarbeitung läuft...') {
        document.getElementById('loading-text').textContent = text;
        document.getElementById('loading-overlay').classList.remove('hidden');
    }

    hideLoading() {
        document.getElementById('loading-overlay').classList.add('hidden');
    }

    showNotice(message, type = 'info', duration = null) {
        const container = document.getElementById('notice-container');
        const notice = document.createElement('div');
        notice.className = `notice ${type}`;

        const icon = this.getNoticeIcon(type);
        const autoHide = duration || this.uxConfig?.frontend_config?.notice_auto_hide || 5000;

        notice.innerHTML = `
            <div class="notice-icon">${icon}</div>
            <div class="notice-content">${message}</div>
            <button class="notice-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;

        container.appendChild(notice);

        // Auto-hide
        if (autoHide > 0) {
            setTimeout(() => {
                if (notice.parentElement) {
                    notice.remove();
                }
            }, autoHide);
        }
    }

    getNoticeIcon(type) {
        const icons = {
            success: '<i class="fas fa-check-circle"></i>',
            error: '<i class="fas fa-exclamation-circle"></i>',
            warning: '<i class="fas fa-exclamation-triangle"></i>',
            info: '<i class="fas fa-info-circle"></i>'
        };
        return icons[type] || icons.info;
    }
}

// Initialize the application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new WebScraperApp();
});