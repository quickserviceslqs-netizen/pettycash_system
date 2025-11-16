/**
 * Alerts Center - Real-time alert notifications with 2-minute auto-refresh
 */

const AlertsManager = {
    refreshInterval: 2 * 60 * 1000, // 2 minutes
    refreshTimer: null,
    companyId: null,

    /**
     * Initialize alerts center
     */
    init(companyId) {
        this.companyId = companyId;
        console.log('Alerts center initialized for company:', companyId);

        // Initial load
        this.refresh();

        // Set up auto-refresh
        this.refreshTimer = setInterval(() => this.refresh(), this.refreshInterval);

        // Cleanup on unload
        window.addEventListener('beforeunload', () => {
            if (this.refreshTimer) {
                clearInterval(this.refreshTimer);
            }
        });

        // Setup tab switching
        this.setupTabs();
    },

    /**
     * Setup tab navigation
     */
    setupTabs() {
        document.querySelectorAll('.alert-tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const severity = e.target.dataset.severity;
                this.showTab(severity);
            });
        });
    },

    /**
     * Show alerts for specific severity
     */
    showTab(severity) {
        document.querySelectorAll('.alert-tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.severity === severity);
        });

        document.querySelectorAll('.alert-group-container').forEach(container => {
            container.classList.toggle('d-none', container.dataset.severity !== severity);
        });
    },

    /**
     * Refresh alerts from API
     */
    refresh() {
        console.log('Refreshing alerts...');

        fetch(`/api/treasury/alerts/?company_id=${this.companyId}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${this.getToken()}`,
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            this.updateAlerts(data.results || data);
            this.updateRefreshTime();
        })
        .catch(error => {
            console.error('Alerts refresh error:', error);
            this.showError('Failed to refresh alerts');
        });
    },

    /**
     * Update alerts UI
     */
    updateAlerts(alerts) {
        // Group by severity
        const grouped = {
            'Critical': [],
            'High': [],
            'Medium': [],
            'Low': []
        };

        alerts.forEach(alert => {
            if (grouped[alert.severity]) {
                grouped[alert.severity].push(alert);
            }
        });

        // Update each group
        Object.entries(grouped).forEach(([severity, items]) => {
            this.updateAlertGroup(severity, items);
        });

        // Update badge counters
        this.updateBadges(grouped);
    },

    /**
     * Update alerts for specific severity group
     */
    updateAlertGroup(severity, alerts) {
        const container = document.getElementById(`alerts-${severity.toLowerCase()}`);
        if (!container) return;

        if (alerts.length === 0) {
            container.innerHTML = `<p class="text-muted text-center py-3">No ${severity.toLowerCase()} alerts</p>`;
            return;
        }

        container.innerHTML = alerts.map(alert => this.createAlertCard(alert)).join('');
    },

    /**
     * Create alert card HTML
     */
    createAlertCard(alert) {
        const badgeClass = this.getSeverityBadgeClass(alert.severity);
        const resolved = alert.resolved || alert.status === 'resolved';
        const resolvedClass = resolved ? 'bg-light' : '';

        return `
            <div class="card ${resolvedClass} mb-2 alert-card" data-alert-id="${alert.alert_id}">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <h6 class="card-title">${alert.title}</h6>
                            <p class="card-text small">${alert.message}</p>
                            <small class="text-muted d-block mt-1">
                                ${alert.related_fund ? `Fund: ${alert.related_fund}` : ''}
                                ${alert.created_at ? `Created: ${this.formatTime(alert.created_at)}` : ''}
                            </small>
                        </div>
                        <span class="badge bg-${badgeClass}">${alert.severity}</span>
                    </div>

                    ${!resolved ? `
                        <div class="mt-3 border-top pt-2">
                            <small class="text-muted d-block mb-2">Alert Actions:</small>
                            <button class="btn btn-sm btn-outline-primary me-2" 
                                    onclick="AlertsManager.acknowledgeAlert('${alert.alert_id}')">
                                Acknowledge
                            </button>
                            <button class="btn btn-sm btn-outline-success" 
                                    onclick="AlertsManager.resolveAlert('${alert.alert_id}')">
                                Resolve
                            </button>
                        </div>
                    ` : `
                        <div class="mt-2">
                            <small class="badge bg-success">✓ Resolved</small>
                        </div>
                    `}
                </div>
            </div>
        `;
    },

    /**
     * Acknowledge alert
     */
    acknowledgeAlert(alertId) {
        fetch(`/api/treasury/alerts/${alertId}/acknowledge/`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.getToken()}`,
                'X-CSRFToken': this.getToken(),
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showSuccess('Alert acknowledged');
                this.refresh();
            }
        })
        .catch(error => console.error('Acknowledge error:', error));
    },

    /**
     * Resolve alert
     */
    resolveAlert(alertId) {
        const card = document.querySelector(`[data-alert-id="${alertId}"]`);
        const notesInput = card?.querySelector('input[placeholder*="Note"]') || prompt('Enter resolution notes:');

        if (!notesInput) return;

        const notes = typeof notesInput === 'string' ? notesInput : notesInput.value;

        fetch(`/api/treasury/alerts/${alertId}/resolve/`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.getToken()}`,
                'X-CSRFToken': this.getToken(),
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ notes: notes })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showSuccess('Alert resolved');
                this.refresh();
            }
        })
        .catch(error => console.error('Resolve error:', error));
    },

    /**
     * Update badge counters
     */
    updateBadges(grouped) {
        Object.entries(grouped).forEach(([severity, items]) => {
            const badge = document.querySelector(`[data-severity="${severity.toLowerCase()}"] .badge`);
            if (badge) {
                badge.textContent = items.length;
                badge.classList.toggle('d-none', items.length === 0);
            }
        });
    },

    /**
     * Get badge class by severity
     */
    getSeverityBadgeClass(severity) {
        const map = {
            'Critical': 'danger',
            'High': 'warning',
            'Medium': 'info',
            'Low': 'secondary'
        };
        return map[severity] || 'info';
    },

    /**
     * Update refresh timestamp
     */
    updateRefreshTime() {
        const element = document.getElementById('alerts-refresh-time');
        if (element) {
            const now = new Date();
            element.textContent = `Updated: ${now.toLocaleTimeString()}`;
        }
    },

    /**
     * Show error message
     */
    showError(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-dismissible fade show';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.querySelector('.container-fluid')?.insertAdjacentElement('afterbegin', alert);
    },

    /**
     * Show success message
     */
    showSuccess(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-success alert-dismissible fade show';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.querySelector('.container-fluid')?.insertAdjacentElement('afterbegin', alert);
    },

    /**
     * Get authentication token
     */
    getToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    },

    /**
     * Format time
     */
    formatTime(isoTime) {
        const date = new Date(isoTime);
        return date.toLocaleString('en-IN', {
            year: '2-digit',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
};

// Export for global access
window.AlertsManager = AlertsManager;
