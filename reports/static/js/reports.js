/**
 * Reports Dashboard - Analytics and Chart.js visualizations
 * Generates payment summaries, fund health, variance analysis, and forecasts
 */

const ReportsManager = {
    charts: {},
    companyId: null,
    selectedMetrics: ['payment_summary', 'fund_health', 'variance_analysis'],

    /**
     * Initialize reports dashboard
     */
    init(companyId) {
        this.companyId = companyId;
        console.log('Reports dashboard initialized for company:', companyId);

        // Setup date range selector
        this.setupDateRangePicker();

        // Initial load
        this.loadReports();

        // Setup export buttons
        this.setupExportButtons();
    },

    /**
     * Setup date range picker
     */
    setupDateRangePicker() {
        const startDateInput = document.getElementById('start-date');
        const endDateInput = document.getElementById('end-date');
        const today = new Date();
        const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);

        if (startDateInput) {
            startDateInput.value = this.formatDateForInput(thirtyDaysAgo);
            startDateInput.addEventListener('change', () => this.loadReports());
        }

        if (endDateInput) {
            endDateInput.value = this.formatDateForInput(today);
            endDateInput.addEventListener('change', () => this.loadReports());
        }
    },

    /**
     * Format date for input element
     */
    formatDateForInput(date) {
        return date.toISOString().split('T')[0];
    },

    /**
     * Setup export buttons
     */
    setupExportButtons() {
        const csvBtn = document.getElementById('export-csv-btn');
        const pdfBtn = document.getElementById('export-pdf-btn');

        if (csvBtn) {
            csvBtn.addEventListener('click', () => this.exportCSV());
        }

        if (pdfBtn) {
            pdfBtn.addEventListener('click', () => this.exportPDF());
        }
    },

    /**
     * Load reports from API
     */
    loadReports() {
        const startDate = document.getElementById('start-date')?.value;
        const endDate = document.getElementById('end-date')?.value;

        if (!startDate || !endDate) return;

        // Load payment summary
        this.loadPaymentSummary(startDate, endDate);

        // Load fund health
        this.loadFundHealth();

        // Load variance analysis
        this.loadVarianceAnalysis(startDate, endDate);

        // Load forecast
        this.loadForecast();
    },

    /**
     * Load payment summary report
     */
    loadPaymentSummary(startDate, endDate) {
        fetch(`/api/treasury/reports/payment_summary/?company_id=${this.companyId}&start_date=${startDate}&end_date=${endDate}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${this.getToken()}`,
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            this.displayPaymentSummary(data);
            this.drawPaymentChart(data);
        })
        .catch(error => {
            console.error('Error loading payment summary:', error);
            this.showError('Failed to load payment summary');
        });
    },

    /**
     * Display payment summary metrics
     */
    displayPaymentSummary(data) {
        const container = document.getElementById('payment-summary-container');
        if (!container) return;

        const totalAmount = parseFloat(data.total_amount || 0).toLocaleString('en-IN', {maximumFractionDigits: 2});
        const successCount = data.by_status?.success?.count || 0;
        const successRate = (data.success_rate || 0).toFixed(1);

        container.innerHTML = `
            <div class="row">
                <div class="col-md-3">
                    <div class="card">
                        <div class="card-body">
                            <h6 class="card-title text-muted">Total Payments</h6>
                            <p class="h4">${data.total_payments || 0}</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card">
                        <div class="card-body">
                            <h6 class="card-title text-muted">Total Amount</h6>
                            <p class="h4">₹${totalAmount}</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card">
                        <div class="card-body">
                            <h6 class="card-title text-muted">Successful</h6>
                            <p class="h4">${successCount}</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card">
                        <div class="card-body">
                            <h6 class="card-title text-muted">Success Rate</h6>
                            <p class="h4">${successRate}%</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * Draw payment status chart
     */
    drawPaymentChart(data) {
        const ctx = document.getElementById('payment-chart');
        if (!ctx) return;

        // Destroy existing chart if any
        if (this.charts.paymentChart) {
            this.charts.paymentChart.destroy();
        }

        const byStatus = data.by_status || {};
        const labels = Object.keys(byStatus);
        const amounts = labels.map(status => byStatus[status].amount || 0);

        this.charts.paymentChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels.map(s => s.charAt(0).toUpperCase() + s.slice(1)),
                datasets: [{
                    data: amounts,
                    backgroundColor: [
                        '#28a745', // success - green
                        '#dc3545', // failed - red
                        '#ffc107'  // pending - yellow
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    },

    /**
     * Load fund health report
     */
    loadFundHealth() {
        fetch(`/api/treasury/reports/fund_health/?company_id=${this.companyId}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${this.getToken()}`,
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            this.displayFundHealth(data);
            this.drawFundHealthChart(data);
        })
        .catch(error => {
            console.error('Error loading fund health:', error);
        });
    },

    /**
     * Display fund health metrics
     */
    displayFundHealth(data) {
        const container = document.getElementById('fund-health-container');
        if (!container) return;

        const totalBalance = parseFloat(data.total_balance || 0).toLocaleString('en-IN', {maximumFractionDigits: 0});
        const utilization = (data.avg_utilization_pct || 0).toFixed(1);

        container.innerHTML = `
            <div class="row">
                <div class="col-md-3">
                    <div class="card">
                        <div class="card-body">
                            <h6 class="card-title text-muted">Total Funds</h6>
                            <p class="h4">${data.total_funds || 0}</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card">
                        <div class="card-body">
                            <h6 class="card-title text-muted">Total Balance</h6>
                            <p class="h4">₹${totalBalance}</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card">
                        <div class="card-body">
                            <h6 class="card-title text-muted">Avg Utilization</h6>
                            <p class="h4">${utilization}%</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card">
                        <div class="card-body">
                            <h6 class="card-title text-muted">Critical</h6>
                            <p class="h4 text-danger">${data.funds_critical || 0}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * Draw fund health chart
     */
    drawFundHealthChart(data) {
        const ctx = document.getElementById('fund-health-chart');
        if (!ctx || !data.fund_details) return;

        if (this.charts.fundHealthChart) {
            this.charts.fundHealthChart.destroy();
        }

        const funds = data.fund_details.slice(0, 10); // Top 10 funds
        const labels = funds.map(f => f.name || f.region);
        const balances = funds.map(f => f.balance || 0);
        const reorders = funds.map(f => f.reorder_level || 0);

        this.charts.fundHealthChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Current Balance',
                        data: balances,
                        backgroundColor: '#007bff'
                    },
                    {
                        label: 'Reorder Level',
                        data: reorders,
                        backgroundColor: '#ffc107'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: { beginAtZero: true }
                },
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    },

    /**
     * Load variance analysis report
     */
    loadVarianceAnalysis(startDate, endDate) {
        fetch(`/api/treasury/reports/variance_analysis/?company_id=${this.companyId}&start_date=${startDate}&end_date=${endDate}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${this.getToken()}`,
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            this.displayVarianceAnalysis(data);
        })
        .catch(error => {
            console.error('Error loading variance analysis:', error);
        });
    },

    /**
     * Display variance analysis
     */
    displayVarianceAnalysis(data) {
        const container = document.getElementById('variance-analysis-container');
        if (!container) return;

        const totalVariance = parseFloat(data.total_variance_amount || 0).toLocaleString('en-IN', {maximumFractionDigits: 2});
        const positiveAmount = parseFloat(data.positive_amount || 0).toLocaleString('en-IN', {maximumFractionDigits: 2});
        const negativeAmount = Math.abs(parseFloat(data.negative_amount || 0)).toLocaleString('en-IN', {maximumFractionDigits: 2});

        container.innerHTML = `
            <div class="row">
                <div class="col-md-3">
                    <div class="card">
                        <div class="card-body">
                            <h6 class="card-title text-muted">Total Variances</h6>
                            <p class="h4">${data.total_variances || 0}</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card">
                        <div class="card-body">
                            <h6 class="card-title text-muted">Total Amount</h6>
                            <p class="h4">₹${totalVariance}</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card">
                        <div class="card-body">
                            <h6 class="card-title text-muted text-success">Favorable</h6>
                            <p class="h4 text-success">₹${positiveAmount}</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card">
                        <div class="card-body">
                            <h6 class="card-title text-muted text-danger">Unfavorable</h6>
                            <p class="h4 text-danger">₹${negativeAmount}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * Load forecast report
     */
    loadForecast() {
        fetch(`/api/treasury/reports/forecast/?company_id=${this.companyId}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${this.getToken()}`,
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            this.displayForecast(data);
        })
        .catch(error => {
            console.error('Error loading forecast:', error);
        });
    },

    /**
     * Display forecast data
     */
    displayForecast(data) {
        const container = document.getElementById('forecast-container');
        if (!container) return;

        const forecasts = data.forecasts || [];
        if (forecasts.length === 0) {
            container.innerHTML = '<p class="text-muted text-center py-3">No forecast data available</p>';
            return;
        }

        container.innerHTML = forecasts.slice(0, 5).map(forecast => `
            <div class="card mb-2">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="card-title">${forecast.fund_name}</h6>
                            <small class="text-muted">Forecast Date: ${forecast.forecast_date}</small>
                        </div>
                        <div class="text-end">
                            ${forecast.needs_replenishment ? '<span class="badge bg-warning">Replenishment Needed</span>' : '<span class="badge bg-success">OK</span>'}
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    },

    /**
     * Export reports as CSV
     */
    exportCSV() {
        const startDate = document.getElementById('start-date')?.value;
        const endDate = document.getElementById('end-date')?.value;

        if (!startDate || !endDate) {
            this.showError('Please select date range');
            return;
        }

        window.location.href = `/api/treasury/reports/export_csv/?company_id=${this.companyId}&start_date=${startDate}&end_date=${endDate}`;
    },

    /**
     * Export reports as PDF
     */
    exportPDF() {
        const startDate = document.getElementById('start-date')?.value;
        const endDate = document.getElementById('end-date')?.value;

        if (!startDate || !endDate) {
            this.showError('Please select date range');
            return;
        }

        window.location.href = `/api/treasury/reports/export_pdf/?company_id=${this.companyId}&start_date=${startDate}&end_date=${endDate}`;
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
     * Get authentication token
     */
    getToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
};

// Export for global access
window.ReportsManager = ReportsManager;
