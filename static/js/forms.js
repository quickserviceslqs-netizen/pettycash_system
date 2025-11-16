// Lightweight forms & OTP helper for Phase 6
(function(window){
    const state = {
        otpInterval: null,
        otpEndTs: null,
    };

    function startOtpCountdown(seconds, onTick, onExpire) {
        stopOtpCountdown();
        state.otpEndTs = Date.now() + (seconds * 1000);

        function tick() {
            const remaining = Math.max(0, state.otpEndTs - Date.now());
            const mins = Math.floor(remaining / 60000);
            const secs = Math.floor((remaining % 60000) / 1000);
            if (typeof onTick === 'function') onTick({ remaining, minutes: mins, seconds: secs });

            if (remaining <= 0) {
                stopOtpCountdown();
                if (typeof onExpire === 'function') onExpire();
            }
        }

        tick();
        state.otpInterval = setInterval(tick, 1000);
        return {
            stop: stopOtpCountdown
        };
    }

    function stopOtpCountdown() {
        if (state.otpInterval) {
            clearInterval(state.otpInterval);
            state.otpInterval = null;
            state.otpEndTs = null;
        }
    }

    function setupOtpForm(options) {
        // options: { inputSelector, timerSelector, verifyBtnSelector, onExpire }
        const input = document.querySelector(options.inputSelector);
        const timerEl = document.querySelector(options.timerSelector);
        const verifyBtn = document.querySelector(options.verifyBtnSelector);

        return {
            start: function(seconds){
                startOtpCountdown(seconds, ({minutes, seconds}) => {
                    if (timerEl) timerEl.textContent = `${minutes}:${seconds.toString().padStart(2,'0')}`;
                    if (verifyBtn) verifyBtn.disabled = !(input && input.value && input.value.length === 6);
                }, function(){
                    if (verifyBtn) verifyBtn.disabled = true;
                    if (options.onExpire) options.onExpire();
                });
            },
            stop: stopOtpCountdown
        };
    }

    window.pc_forms = {
        startOtpCountdown,
        stopOtpCountdown,
        setupOtpForm
    };
})(window);
