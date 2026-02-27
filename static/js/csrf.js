/**
 * CSRF Auto-Injection
 * Injects CSRF token into all POST forms, HTMX requests, and fetch() calls.
 * Reads the token from <meta name="csrf-token"> set by the server.
 */
(function () {
    var meta = document.querySelector('meta[name="csrf-token"]');
    var token = meta ? meta.getAttribute("content") : "";
    if (!token) return;

    function ensureToken(form) {
        var method = (form.getAttribute("method") || "get").toLowerCase();
        if (method !== "post") return;
        if (form.querySelector('input[name="csrf_token"]')) return;
        var input = document.createElement("input");
        input.type = "hidden";
        input.name = "csrf_token";
        input.value = token;
        form.appendChild(input);
    }

    function scanForms(root) {
        var scope = root || document;
        scope.querySelectorAll("form").forEach(ensureToken);
    }

    scanForms();

    // Inject CSRF header into all HTMX requests
    document.body.addEventListener("htmx:configRequest", function (event) {
        event.detail.headers["X-CSRF-Token"] = token;
    });

    // Re-scan forms after HTMX swaps in new content
    document.body.addEventListener("htmx:afterSwap", function (event) {
        scanForms(event.target);
    });

    // Monkey-patch fetch() to include CSRF header on all requests
    var originalFetch = window.fetch;
    window.fetch = function (resource, options) {
        var opts = options || {};
        var headers = new Headers(opts.headers || {});
        if (!headers.has("X-CSRF-Token")) {
            headers.set("X-CSRF-Token", token);
        }
        opts.headers = headers;
        return originalFetch(resource, opts);
    };
})();
