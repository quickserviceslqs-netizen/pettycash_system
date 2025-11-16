(function(window){
    function formatCurrency(value){
        if (typeof value !== 'number') value = parseFloat(value) || 0;
        return '₹' + value.toLocaleString('en-IN', { maximumFractionDigits: 2 });
    }

    function showToast(message, type='info', dismissMs=5000){
        const container = document.querySelector('main') || document.body;
        const div = document.createElement('div');
        div.className = `alert alert-${type} alert-dismissible fade show`;
        div.role = 'alert';
        div.innerHTML = `${message} <button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
        container.insertAdjacentElement('afterbegin', div);
        setTimeout(()=>{ try { const bs = bootstrap.Alert.getOrCreateInstance(div); bs.close(); } catch(e){} }, dismissMs);
    }

    window.pc_ui = { formatCurrency, showToast };
})(window);