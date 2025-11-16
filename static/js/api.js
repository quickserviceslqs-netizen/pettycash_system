(function(window){
    // Simple API wrapper for fetch with CSRF and Token handling
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function getAuthToken() {
        // Try common cookie names, fallback to null
        return getCookie('auth_token') || getCookie('token') || null;
    }

    async function request(url, method='GET', data=null, opts={}){
        const headers = opts.headers || {};
        headers['Accept'] = 'application/json';
        if (method !== 'GET' && method !== 'HEAD'){
            headers['X-CSRFToken'] = getCookie('csrftoken');
            headers['Content-Type'] = 'application/json';
        }
        const token = getAuthToken();
        if (token) headers['Authorization'] = 'Token ' + token;

        const fetchOpts = Object.assign({
            method: method,
            headers: headers,
            credentials: 'same-origin'
        }, opts.fetchOptions || {});

        if (data) fetchOpts.body = JSON.stringify(data);

        try {
            const res = await fetch(url, fetchOpts);
            const contentType = res.headers.get('content-type') || '';
            let body = null;
            if (contentType.includes('application/json')) {
                body = await res.json();
            } else {
                body = await res.text();
            }

            if (!res.ok) {
                const err = new Error('HTTP error, status = ' + res.status);
                err.status = res.status;
                err.body = body;
                throw err;
            }

            return body;
        } catch (err) {
            // Basic retry for transient network errors (1 retry)
            if (!opts._retry) {
                opts._retry = true;
                return request(url, method, data, opts);
            }
            throw err;
        }
    }

    function get(url, opts){ return request(url, 'GET', null, opts); }
    function post(url, data, opts){ return request(url, 'POST', data, opts); }
    function patch(url, data, opts){ return request(url, 'PATCH', data, opts); }
    function del(url, opts){ return request(url, 'DELETE', null, opts); }

    window.pc_api = {
        request, get, post, patch, del, getCookie, getAuthToken
    };

})(window);