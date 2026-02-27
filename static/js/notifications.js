/**
 * Notification Bell Alpine.js component.
 * Used in admin/base.html via x-data="notificationBell()".
 * Connects to WebSocket for real-time notifications and provides
 * fetch-based read/unread management.
 */
function notificationBell() {
    return {
        open: false,
        unreadCount: 0,
        notifications: [],
        ws: null,
        reconnectTimer: null,

        init: function () {
            this.fetchNotifications();
            this.connectWebSocket();
            var self = this;
            setInterval(function () { self.fetchUnreadCount(); }, 60000);
        },

        toggle: function () {
            this.open = !this.open;
            if (this.open) this.fetchNotifications();
        },

        fetchNotifications: async function () {
            try {
                var token = this.getToken();
                if (!token) return;
                var resp = await fetch("/notifications/me?limit=10", {
                    headers: { Authorization: "Bearer " + token },
                });
                if (resp.ok) {
                    var data = await resp.json();
                    this.notifications = data.items || [];
                    this.fetchUnreadCount();
                }
            } catch (e) {
                console.debug("[Notifications] fetch failed:", e);
            }
        },

        fetchUnreadCount: async function () {
            try {
                var token = this.getToken();
                if (!token) return;
                var resp = await fetch("/notifications/me/unread-count", {
                    headers: { Authorization: "Bearer " + token },
                });
                if (resp.ok) {
                    var data = await resp.json();
                    this.unreadCount = data.count;
                }
            } catch (e) {
                // Silently ignore count fetch failures
            }
        },

        markRead: async function (n) {
            if (n.is_read) return;
            try {
                var token = this.getToken();
                if (!token) return;
                await fetch("/notifications/me/" + n.id + "/read", {
                    method: "POST",
                    headers: { Authorization: "Bearer " + token },
                });
                n.is_read = true;
                this.unreadCount = Math.max(0, this.unreadCount - 1);
            } catch (e) {
                // Silently ignore mark-read failures
            }
        },

        markAllRead: async function () {
            try {
                var token = this.getToken();
                if (!token) return;
                await fetch("/notifications/me/read-all", {
                    method: "POST",
                    headers: { Authorization: "Bearer " + token },
                });
                this.notifications.forEach(function (n) { n.is_read = true; });
                this.unreadCount = 0;
            } catch (e) {
                // Silently ignore mark-all-read failures
            }
        },

        connectWebSocket: function () {
            var self = this;
            var token = this.getToken();
            if (!token) return;
            var protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
            var wsUrl =
                protocol + "//" + window.location.host + "/ws/notifications?token=" + token;
            try {
                this.ws = new WebSocket(wsUrl);
                this.ws.onmessage = function (event) {
                    try {
                        var data = JSON.parse(event.data);
                        if (data.type === "notification") {
                            self.unreadCount++;
                            self.notifications.unshift(data.notification);
                            if (self.notifications.length > 10) self.notifications.pop();
                            window.showToast(data.notification.title, "info");
                        }
                    } catch (e) {
                        // Ignore malformed WebSocket messages
                    }
                };
                this.ws.onclose = function () { self.scheduleReconnect(); };
                this.ws.onerror = function () {
                    if (self.ws) self.ws.close();
                };
            } catch (e) {
                this.scheduleReconnect();
            }
        },

        scheduleReconnect: function () {
            var self = this;
            if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
            this.reconnectTimer = setTimeout(function () {
                self.connectWebSocket();
            }, 5000);
        },

        getToken: function () {
            var match = document.cookie.match(/(?:^|;\s*)access_token=([^;]*)/);
            return match ? match[1] : "";
        },

        destroy: function () {
            if (this.ws) {
                this.ws.close();
                this.ws = null;
            }
            if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
        },
    };
}
