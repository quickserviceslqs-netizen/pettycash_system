(function(window){
    // Chart helpers for reports using Chart.js
    const charts = {};

    function destroyChart(key){
        if (charts[key]){
            try { charts[key].destroy(); } catch(e) { /* ignore */ }
            delete charts[key];
        }
    }

    function createDoughnut(key, ctx, labels, dataArr, options){
        destroyChart(key);
        charts[key] = new Chart(ctx, Object.assign({
            type: 'doughnut',
            data: { labels: labels, datasets: [{ data: dataArr, backgroundColor: options && options.colors || ['#0d6efd','#198754','#ffc107','#dc3545'] }] },
            options: Object.assign({ responsive:true, maintainAspectRatio:false }, options && options.cfg)
        }, {}));
        return charts[key];
    }

    function createLine(key, ctx, labels, dataArr, cfg){
        destroyChart(key);
        charts[key] = new Chart(ctx, Object.assign({
            type: 'line',
            data: { labels: labels, datasets: [{ label: cfg && cfg.label || 'Data', data: dataArr, borderColor: cfg && cfg.color || '#0d6efd', backgroundColor: cfg && cfg.bg || 'rgba(13,110,253,0.1)', tension: 0.4, fill:true }] },
            options: Object.assign({ responsive:true, maintainAspectRatio:false }, cfg && cfg.options)
        }, {}));
        return charts[key];
    }

    window.pc_reports = { destroyChart, createDoughnut, createLine };
})(window);