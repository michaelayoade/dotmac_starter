/**
 * Global application scripts.
 * Reads auth state from <body data-auth-enabled="true|false">.
 */

// ═══════════════════════════════════════════════════════════════════
// Auth state — read from body data attribute (set by server template)
// ═══════════════════════════════════════════════════════════════════
window.__authEnabled = document.body.dataset.authEnabled === "true";

// ═══════════════════════════════════════════════════════════════════
// Toast Notification Store (Alpine.js component)
// ═══════════════════════════════════════════════════════════════════
function toastStore() {
    return {
        toasts: [],
        addToast: function (detail) {
            var id = Date.now();
            this.toasts.push({
                id: id,
                message: detail.message,
                type: detail.type || "info",
                visible: true,
            });
            var self = this;
            setTimeout(function () { self.removeToast(id); }, detail.duration || 4000);
        },
        removeToast: function (id) {
            var toast = this.toasts.find(function (t) { return t.id === id; });
            if (toast) {
                toast.visible = false;
                var self = this;
                setTimeout(function () {
                    self.toasts = self.toasts.filter(function (t) { return t.id !== id; });
                }, 300);
            }
        },
    };
}

// Global helper: window.showToast('message', 'success')
window.showToast = function (message, type, duration) {
    window.dispatchEvent(
        new CustomEvent("show-toast", {
            detail: { message: message, type: type || "info", duration: duration || 4000 },
        })
    );
};

// ═══════════════════════════════════════════════════════════════════
// Query-Parameter Toast Consumer
// Shows toast messages from URL params (?success=, ?error=, etc.)
// then cleans the URL to prevent re-display on refresh.
// ═══════════════════════════════════════════════════════════════════
(function consumeQueryMessages() {
    var params = new URLSearchParams(window.location.search);
    var keys = ["error", "success", "warning", "info", "created", "updated", "deleted"];
    var changed = false;

    keys.forEach(function (key) {
        if (!params.has(key)) return;
        var value = params.get(key);
        if (value) {
            var type =
                key === "error" ? "error" :
                key === "warning" ? "warning" :
                key === "info" ? "info" :
                "success";
            window.dispatchEvent(
                new CustomEvent("show-toast", { detail: { message: value, type: type } })
            );
        }
        params.delete(key);
        changed = true;
    });

    if (changed) {
        var newQuery = params.toString();
        var newUrl =
            window.location.pathname +
            (newQuery ? "?" + newQuery : "") +
            window.location.hash;
        window.history.replaceState({}, "", newUrl);
    }
})();

// HTMX event listeners for toasts
document.body.addEventListener("htmx:afterRequest", function (evt) {
    var trigger = evt.detail.xhr.getResponseHeader("HX-Trigger");
    if (trigger) {
        try {
            var data = JSON.parse(trigger);
            if (data.showToast) {
                window.dispatchEvent(
                    new CustomEvent("show-toast", { detail: data.showToast })
                );
            }
        } catch (e) {
            // Non-JSON trigger header — ignore
        }
    }
});

// ═══════════════════════════════════════════════════════════════════
// Automatic Token Refresh Manager
// Keeps users logged in by refreshing access tokens periodically.
// ═══════════════════════════════════════════════════════════════════
(function () {
    var REFRESH_INTERVAL_MS = 10 * 60 * 1000; // Every 10 minutes
    var MIN_REFRESH_INTERVAL_MS = 30000; // Don't refresh more than once per 30s

    var refreshTimeoutId = null;
    var lastRefreshTime = 0;
    var refreshDisabled = false;
    var refreshInProgress = false;

    async function refreshToken() {
        if (!window.__authEnabled || refreshDisabled || refreshInProgress) return;
        var currentPath = window.location.pathname;
        if (currentPath === "/login" || currentPath === "/admin/login") return;
        var now = Date.now();
        if (now - lastRefreshTime < MIN_REFRESH_INTERVAL_MS) {
            scheduleNextRefresh();
            return;
        }

        refreshInProgress = true;
        try {
            var response = await fetch("/auth/refresh", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify({}),
            });

            if (response.ok) {
                await response.json();
                lastRefreshTime = Date.now();
                console.debug("[Auth] Token refreshed successfully");
            } else if (response.status === 401) {
                console.debug("[Auth] Session expired, redirecting to login");
                refreshDisabled = true;
                var redirectTarget = window.location.pathname + window.location.search;
                if (currentPath !== "/login" && currentPath !== "/") {
                    window.location.href = "/login?next=" + encodeURIComponent(redirectTarget);
                }
                return;
            }
        } catch (e) {
            console.debug("[Auth] Token refresh failed:", e.message);
        } finally {
            refreshInProgress = false;
        }

        scheduleNextRefresh();
    }

    function scheduleNextRefresh() {
        if (!window.__authEnabled || refreshDisabled) return;
        if (refreshTimeoutId) clearTimeout(refreshTimeoutId);
        refreshTimeoutId = setTimeout(refreshToken, REFRESH_INTERVAL_MS);
    }

    function onUserActivity() {
        if (!window.__authEnabled || refreshDisabled) return;
        if (Date.now() - lastRefreshTime < MIN_REFRESH_INTERVAL_MS) return;
        scheduleNextRefresh();
    }

    ["click", "keydown", "scroll", "touchstart"].forEach(function (event) {
        document.addEventListener(event, onUserActivity, { passive: true });
    });

    if (window.__authEnabled) scheduleNextRefresh();

    document.addEventListener("visibilitychange", function () {
        if (
            document.visibilityState === "visible" &&
            window.__authEnabled &&
            !refreshDisabled
        ) {
            var elapsed = Date.now() - lastRefreshTime;
            if (elapsed >= REFRESH_INTERVAL_MS) {
                refreshToken();
            } else {
                scheduleNextRefresh();
            }
        }
    });
})();

// ═══════════════════════════════════════════════════════════════════
// Form Double-Submit Protection
// Disables submit buttons after first click to prevent duplicates.
// ═══════════════════════════════════════════════════════════════════
document.addEventListener("DOMContentLoaded", function () {
    document.addEventListener("submit", function (e) {
        var form = e.target;
        if (!form || form.tagName !== "FORM") return;
        var method = (form.method || "GET").toUpperCase();
        if (method !== "POST") return;

        var btn = form.querySelector('button[type="submit"], input[type="submit"]');
        if (btn && !btn.disabled) {
            btn.disabled = true;
            btn.dataset.originalText = btn.textContent;
            btn.textContent = "Processing\u2026";
            // Re-enable after 8s in case of error (no redirect)
            setTimeout(function () {
                btn.disabled = false;
                if (btn.dataset.originalText) {
                    btn.textContent = btn.dataset.originalText;
                }
            }, 8000);
        }
    });
});
