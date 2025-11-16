/**
 * Treasury Dashboard - Real-time metrics and auto-refresh
 * Fetches dashboard data every 5 minutes and updates UI
 */

const DashboardManager = {
    refreshInterval: 5 * 60 * 1000, // 5 minutes
    refreshTimer: null,
    companyId: null,

    /**
     * Initialize dashboard with auto-refresh
     */
    init(companyId) {
        this.companyId = companyId;
        console.log('Dashboard initialized for company:', companyId);
        
        // Initial load
        this.refresh();
        
        // Set up auto-refresh
        this.refreshTimer = setInterval(() => this.refresh(), this.refreshInterval);
        
        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            if (this.refreshTimer) {
                clearInterval(this.refreshTimer);
            }
        });
    },

    /**
     * Refresh dashboard data via AJAX
     */
    refresh() {
        console.log('Refreshing dashboard...');
        
        // Fetch dashboard summary
        fetch(`/api/treasury/dashboard/${this.companyId}/`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${this.getToken()}`,
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            this.updateDashboard(data);
            this.showRefreshTime();
        })
        .catch(error => {
            console.error('Dashboard refresh error:', error);
            this.showError('Failed to refresh dashboard');
        });
    },

    /**
     * Update dashboard UI with new data
     */
    updateDashboard(data) {
        // Update metric cards
        if (data.total_funds !== undefined) {
            this.updateMetric('total-funds', data.total_funds);
        }
        if (data.total_balance !== undefined) {
            this.updateMetric('total-balance', `₹${parseFloat(data.total_balance).toLocaleString('en-IN', {maximumFractionDigits: 2})}`);
        }
        if (data.funds_below_reorder !== undefined) {
            this.updateMetric('funds-warning', data.funds_below_reorder);
            if (data.funds_below_reorder > 0) {
                document.getElementById('warning-badge')?.classList.remove('d-none');
            }
        }
        if (data.funds_critical !== undefined) {
            this.updateMetric('funds-critical', data.funds_critical);
            if (data.funds_critical > 0) {
                document.getElementById('critical-badge')?.classList.remove('d-none');
            }
        }

        // Update fund status cards
        if (data.funds) {
            this.updateFundCards(data.funds);
        }

        // Update pending payments
        if (data.pending_payments) {
            this.updatePendingPayments(data.pending_payments);
        }

        // Update recent payments
        if (data.recent_payments) {
            this.updateRecentPayments(data.recent_payments);
        }

        // Update alerts
        if (data.active_alerts) {
            this.updateAlerts(data.active_alerts);
        }
    },

    /**
     * Update metric card value
     */
    updateMetric(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
        }
    },

    /**
     * Update fund status cards
     */
    updateFundCards(funds) {
        const container = document.getElementById('fund-cards');
        if (!container) return;

        container.innerHTML = '';
        funds.forEach(fund => {
            const card = this.createFundCard(fund);
            container.appendChild(card);
        });
    },

    /**
     * Create fund status card HTML
     */
    createFundCard(fund) {
        const card = document.createElement('div');
        card.className = 'col-md-6 mb-4';
        
        const statusClass = fund.status === 'OK' ? 'success' : 
                          fund.status === 'WARNING' ? 'warning' : 'danger';
        const statusIcon = fund.status === 'OK' ? '✓' : 
                          fund.status === 'WARNING' ? '⚠' : '🔴';

        card.innerHTML = `
            <div class="card border-${statusClass} shadow-sm">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h6 class="card-title">${fund.name}</h6>
                        <span class="badge bg-${statusClass}">${statusIcon} ${fund.status}</span>
                    </div>
                    <div class="row text-sm">
                        <div class="col-6">
                            <p class="text-muted mb-1">Balance</p>
                            <p class="h6">₹${parseFloat(fund.current_balance).toLocaleString('en-IN', {maximumFractionDigits: 0})}</p>
                        </div>
                        <div class="col-6">
                            <p class="text-muted mb-1">Reorder Level</p>
                            <p class="h6">₹${parseFloat(fund.reorder_level).toLocaleString('en-IN', {maximumFractionDigits: 0})}</p>
                        </div>
                    </div>
                    <div class="mt-3">
                        <small class="text-muted">Utilization: ${fund.utilization_pct.toFixed(1)}%</small>
                        <div class="progress mt-1">
                            <div class="progress-bar bg-${statusClass}" style="width: ${Math.min(fund.utilization_pct, 100)}%"></div>
                        </div>
                    </div>
                    <small class="text-muted d-block mt-2">
                        ${fund.transaction_count} transaction(s) today
                    </small>
                </div>
            </div>
        `;

        return card;
    },

    /**
     * Update pending payments list
     */
    updatePendingPayments(payments) {
        const container = document.getElementById('pending-payments-list');
        if (!container) return;

        if (payments.length === 0) {
            container.innerHTML = '<p class="text-muted text-center py-3">No pending payments</p>';
            return;
        }

        container.innerHTML = payments.map(payment => `
            <div class="list-group-item px-0 py-3 border-bottom">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <p class="fw-bold mb-1">${payment.requisition.transaction_id}</p>
                        <small class="text-muted">${payment.requisition.purpose}</small>
                    </div>
                    <div class="text-end">
                        <p class="fw-bold mb-1">₹${parseFloat(payment.amount).toLocaleString('en-IN', {maximumFractionDigits: 2})}</p>
                        <button class="btn btn-sm btn-primary" onclick="PaymentManager.executePayment('${payment.payment_id}')">
                            Execute
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    },

    /**
     * Update recent payments list
     */
    updateRecentPayments(payments) {
        const container = document.getElementById('recent-payments-list');
        if (!container) return;

        if (payments.length === 0) {
            container.innerHTML = '<p class="text-muted text-center py-3">No recent payments</p>';
            return;
        }

        container.innerHTML = payments.map(payment => {
            const statusBg = payment.status === 'success' ? 'success' : 'danger';
            const statusIcon = payment.status === 'success' ? '✓' : '✗';
            const timeAgo = this.getTimeAgo(payment.updated_at);

            return `
                <div class="list-group-item px-0 py-2 border-bottom">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <p class="fw-bold mb-0">${payment.requisition.transaction_id}</p>
                            <small class="text-muted">${timeAgo}</small>
                        </div>
                        <div class="text-end">
                            <p class="fw-bold mb-0">₹${parseFloat(payment.amount).toLocaleString('en-IN', {maximumFractionDigits: 2})}</p>
                            <span class="badge bg-${statusBg}">${statusIcon} ${payment.status}</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    },

    /**
     * Update alerts widget
     */
    updateAlerts(alerts) {
        const container = document.getElementById('alerts-widget');
        if (!container) return;

        // Group alerts by severity
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

        let html = '';
        Object.entries(grouped).forEach(([severity, items]) => {
            if (items.length > 0) {
                const icon = severity === 'Critical' ? '🔴' : severity === 'High' ? '⚠' : 'ℹ';
                html += `<div class="alert-group mb-2">
                    <small class="text-muted">${icon} ${severity} (${items.length})</small>
                    ${items.map(alert => `
                        <div class="alert alert-${this.getSeverityClass(severity)} py-2 mb-1">
                            ${alert.title}
                        </div>
                    `).join('')}
                </div>`;
            }
        });

        container.innerHTML = html || '<p class="text-muted text-center py-3">No active alerts</p>';
    },

    /**
     * Get Bootstrap alert class by severity
     */
    getSeverityClass(severity) {
        const map = {
            'Critical': 'danger',
            'High': 'warning',
            'Medium': 'info',
            'Low': 'secondary'
        };
        return map[severity] || 'info';
    },

    /**
     * Show refresh timestamp
     */
    showRefreshTime() {
        const element = document.getElementById('last-refresh-time');
        if (element) {
            const now = new Date();
            element.textContent = `Updated at ${now.toLocaleTimeString()}`;
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
     * Get authentication token from cookie
     */
    getToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    },

    /**
     * Format time ago
     */
    getTimeAgo(isoTime) {
        const now = new Date();
        const then = new Date(isoTime);
        const seconds = Math.floor((now - then) / 1000);

        if (seconds < 60) return 'just now';
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes}m ago`;
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours}h ago`;
        const days = Math.floor(hours / 24);
        return `${days}d ago`;
    }
};

// Export for global access
window.DashboardManager = DashboardManager;
