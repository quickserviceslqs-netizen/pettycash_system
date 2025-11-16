(function(window){
    // Alerts polling helper
    const DEFAULT_INTERVAL_MS = 2 * 60 * 1000; // 2 minutes
    let _intervalId = null;

    async function fetchAlerts(){
        try {
            const data = await window.pc_api.get('/api/alerts/active/');
            if (window.onAlertsUpdate && typeof window.onAlertsUpdate === 'function'){
                window.onAlertsUpdate(data.active_alerts || data);
            }
            return data;
        } catch (err){
            console.error('alerts.js: fetchAlerts error', err);
            return null;
        }
    }

    function startPolling(ms){
        stopPolling();
        const interval = ms || DEFAULT_INTERVAL_MS;
        // initial fetch
        fetchAlerts();
        _intervalId = setInterval(fetchAlerts, interval);
    }

    function stopPolling(){
        if (_intervalId) {
            clearInterval(_intervalId);
            _intervalId = null;
        }
    }

    window.pc_alerts = {
        startPolling,
        stopPolling,
        fetchAlerts
    };

})(window);