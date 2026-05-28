/* Chat widget — IIFE, polling-based.

   The widget polls /chat/api/state/ every POLL_MS to keep the unread badge
   and conversation list current. While a conversation is open, it also polls
   /chat/api/conversations/<id>/messages/?after=<lastSeenId> for incremental
   message appends. State is intentionally kept simple — server is the source
   of truth; the UI just reflects.

   Permissions are enforced server-side; this script only handles the UI. */
(function () {
    'use strict';

    var POLL_MS = 4000;

    // --- DOM refs (resolved on init) -----------------------------------------
    var $widget, $toggle, $panel, $badge, $title, $back, $close;
    var $viewList, $viewConv, $viewPicker;
    var $list, $actions, $empty;
    var $convMeta, $messages, $form, $input, $readonly;
    var $pickerInput, $pickerResults;

    // --- state ---------------------------------------------------------------
    var state = {
        isRep: false,
        isLab: false,
        conversations: [],
        view: 'list',          // 'list' | 'conv' | 'picker'
        activeConvId: null,
        activeConv: null,      // the active conversation object (from state)
        lastSeenMsgId: 0,
        pickerQuery: '',
        showArchived: false,   // list-view toggle: see active vs archived
    };
    var pollTimer = null;
    var pickerTimer = null;
    var csrf = '';

    // --- helpers -------------------------------------------------------------
    function $(id) { return document.getElementById(id); }

    function escapeHTML(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function timeLabel(iso) {
        if (!iso) return '';
        var d = new Date(iso);
        var now = new Date();
        var sameDay = d.toDateString() === now.toDateString();
        if (sameDay) {
            return d.toLocaleTimeString([], {hour: 'numeric', minute: '2-digit'});
        }
        var diff = (now - d) / 86400000;
        if (diff < 7) {
            return d.toLocaleDateString([], {weekday: 'short'});
        }
        return d.toLocaleDateString([], {month: 'short', day: 'numeric'});
    }

    function fetchJSON(url, opts) {
        opts = opts || {};
        opts.headers = opts.headers || {};
        opts.headers['X-Requested-With'] = 'XMLHttpRequest';
        opts.credentials = 'same-origin';
        if (opts.method && opts.method !== 'GET') {
            opts.headers['X-CSRFToken'] = csrf;
            if (opts.body && typeof opts.body !== 'string') {
                opts.headers['Content-Type'] = 'application/json';
                opts.body = JSON.stringify(opts.body);
            }
        }
        return fetch(url, opts).then(function (r) {
            if (!r.ok) {
                return r.text().then(function (t) {
                    var err = new Error('HTTP ' + r.status);
                    err.status = r.status;
                    err.body = t;
                    throw err;
                });
            }
            return r.json();
        });
    }

    // --- views ---------------------------------------------------------------
    function showView(name) {
        state.view = name;
        $viewList.hidden = name !== 'list';
        $viewConv.hidden = name !== 'conv';
        $viewPicker.hidden = name !== 'picker';
        $back.hidden = name === 'list';
        if (name === 'list') $title.textContent = 'Messages';
        else if (name === 'picker') $title.textContent = 'New direct message';
    }

    function openPanel() {
        $panel.hidden = false;
        try { localStorage.setItem('chat.open', 'true'); } catch (e) {}
    }
    function closePanel() {
        $panel.hidden = true;
        try { localStorage.setItem('chat.open', 'false'); } catch (e) {}
    }
    function isPanelOpen() { return !$panel.hidden; }

    // --- rendering -----------------------------------------------------------
    function renderBadge(total) {
        if (!total) {
            $badge.hidden = true;
            $badge.textContent = '0';
            return;
        }
        $badge.hidden = false;
        $badge.textContent = total > 99 ? '99+' : String(total);
    }

    function findConv(id) {
        for (var i = 0; i < state.conversations.length; i++) {
            if (state.conversations[i].id === id) return state.conversations[i];
        }
        return null;
    }

    function renderActions() {
        $actions.innerHTML = '';
        if (state.isLab) {
            var hasOpen = state.conversations.some(function (c) {
                return c.kind === 'support' && !c.is_closed;
            });
            if (!hasOpen) {
                var b = document.createElement('button');
                b.type = 'button';
                b.textContent = 'Start chat with AMS support';
                b.addEventListener('click', startSupportChat);
                $actions.appendChild(b);
            }
        } else if (state.isRep) {
            var dm = document.createElement('button');
            dm.type = 'button';
            dm.textContent = 'New direct message';
            dm.addEventListener('click', function () {
                $pickerInput.value = '';
                state.pickerQuery = '';
                $pickerResults.innerHTML = '';
                showView('picker');
                setTimeout(function () { $pickerInput.focus(); }, 0);
                searchUsers('');
            });
            $actions.appendChild(dm);
        }
        // Archived toggle is available to everyone (label flips based on mode).
        var arch = document.createElement('button');
        arch.type = 'button';
        arch.textContent = state.showArchived ? 'Active' : 'Archived';
        arch.title = state.showArchived ? 'Back to active chats' : 'Show archived chats';
        arch.addEventListener('click', function () {
            state.showArchived = !state.showArchived;
            loadState();
        });
        $actions.appendChild(arch);
    }

    function renderList() {
        renderActions();
        $list.innerHTML = '';
        $empty.hidden = state.conversations.length > 0;

        function makeItem(c) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'chat-list-item';
            btn.addEventListener('click', function () { openConversation(c.id); });

            var inner = document.createElement('div');
            inner.className = 'chat-li-body';

            var name = document.createElement('div');
            name.className = 'chat-li-name';
            var nameSpan = document.createElement('span');
            nameSpan.textContent = c.peer_name || '(no name)';
            name.appendChild(nameSpan);
            if (c.kind === 'support' && state.isRep) {
                var tag = document.createElement('span');
                tag.className = 'chat-li-tag';
                if (c.is_closed) {
                    tag.classList.add('closed');
                    tag.textContent = 'Closed';
                } else if (!c.claimed_by_id) {
                    tag.classList.add('unclaimed');
                    tag.textContent = 'Unclaimed';
                } else {
                    tag.textContent = 'Claimed: ' + (c.claimed_by_name || '');
                }
                name.appendChild(tag);
            } else if (c.is_closed) {
                var t2 = document.createElement('span');
                t2.className = 'chat-li-tag closed';
                t2.textContent = 'Closed';
                name.appendChild(t2);
            }
            inner.appendChild(name);

            var snip = document.createElement('div');
            snip.className = 'chat-li-snippet';
            snip.textContent = c.last_snippet || '(no messages yet)';
            inner.appendChild(snip);

            var t = document.createElement('div');
            t.className = 'chat-li-time';
            t.textContent = timeLabel(c.last_message_at);
            inner.appendChild(t);

            btn.appendChild(inner);
            if (c.unread_count > 0) {
                var dot = document.createElement('span');
                dot.className = 'chat-li-unread';
                btn.appendChild(dot);
            }
            return btn;
        }

        if (state.isRep) {
            var support = state.conversations.filter(function (c) { return c.kind === 'support'; });
            var dms = state.conversations.filter(function (c) { return c.kind === 'dm'; });
            // Unclaimed support first, then claimed, then closed.
            support.sort(function (a, b) {
                if (a.is_closed !== b.is_closed) return a.is_closed ? 1 : -1;
                var ua = a.claimed_by_id ? 1 : 0, ub = b.claimed_by_id ? 1 : 0;
                if (ua !== ub) return ua - ub;
                return 0;
            });
            if (support.length) {
                var h1 = document.createElement('div');
                h1.className = 'chat-list-section';
                h1.textContent = 'Support';
                $list.appendChild(h1);
                support.forEach(function (c) { $list.appendChild(makeItem(c)); });
            }
            if (dms.length) {
                var h2 = document.createElement('div');
                h2.className = 'chat-list-section';
                h2.textContent = 'Direct messages';
                $list.appendChild(h2);
                dms.forEach(function (c) { $list.appendChild(makeItem(c)); });
            }
        } else {
            state.conversations.forEach(function (c) { $list.appendChild(makeItem(c)); });
        }
    }

    function renderConvMeta(c) {
        $convMeta.innerHTML = '';
        if (!c) return;
        var label = document.createElement('span');
        if (c.kind === 'support' && state.isRep) {
            label.textContent = c.lab_user_name ? ('Lab: ' + c.lab_user_name) : 'Support chat';
        } else if (c.kind === 'support') {
            label.textContent = c.claimed_by_name
                ? ('AMS Support · ' + c.claimed_by_name)
                : 'AMS Support (unclaimed)';
        } else {
            label.textContent = c.peer_name || '';
        }
        $convMeta.appendChild(label);

        function btn(text, cls, fn) {
            var b = document.createElement('button');
            b.type = 'button';
            b.textContent = text;
            if (cls) b.classList.add(cls);
            b.addEventListener('click', fn);
            return b;
        }

        if (c.kind === 'support' && state.isRep && !c.is_closed) {
            if (!c.claimed_by_id) {
                $convMeta.appendChild(btn('Claim', null, function () { claimChat(c.id); }));
            } else if (c.claimed_by_id === peerSelfId()) {
                $convMeta.appendChild(btn('Release', null, function () { unclaimChat(c.id); }));
            }
        }
        if (!c.is_closed && (state.isRep || (c.kind === 'support' && state.isLab))) {
            $convMeta.appendChild(btn('Close', 'danger', function () { closeChat(c.id); }));
        }
        if (c.is_archived) {
            $convMeta.appendChild(btn('Unarchive', null, function () { unarchiveChat(c.id); }));
        } else {
            $convMeta.appendChild(btn('Archive', null, function () { archiveChat(c.id); }));
        }
    }

    // We don't ship the current user id; deduce it indirectly via 'is_mine' on
    // messages and the can_reply flag. For "is this MY claim?" we rely on the
    // server flagging can_reply correctly.
    function peerSelfId() {
        // Look at any message we sent for our user id, or null.
        for (var i = state.activeMessages.length - 1; i >= 0; i--) {
            if (state.activeMessages[i].is_mine) return state.activeMessages[i].sender_id;
        }
        return null;
    }
    state.activeMessages = [];

    // Track which message ids are already rendered. Polling can race with
    // a Send response: the poll fetch was issued BEFORE lastSeenMsgId got
    // bumped by the send-response render, so the poll's reply contains the
    // just-sent message and we'd render it twice. This Set blocks that.
    var renderedIds = new Set();

    function renderMessages(msgs, appendOnly) {
        if (!appendOnly) {
            $messages.innerHTML = '';
            renderedIds.clear();
            state.activeMessages = [];
        }
        msgs.forEach(function (m) {
            if (renderedIds.has(m.id)) return;
            renderedIds.add(m.id);
            var div = document.createElement('div');
            div.className = 'chat-msg ' + (m.is_mine ? 'mine' : 'theirs');
            if (!m.is_mine) {
                var s = document.createElement('div');
                s.className = 'chat-msg-sender';
                s.textContent = m.sender_name;
                div.appendChild(s);
            }
            var body = document.createElement('div');
            body.textContent = m.body;
            div.appendChild(body);
            $messages.appendChild(div);
            if (m.id > state.lastSeenMsgId) state.lastSeenMsgId = m.id;
            state.activeMessages.push(m);
        });
        $messages.scrollTop = $messages.scrollHeight;
    }

    function renderReplyBox(c) {
        if (c && c.can_reply) {
            $form.hidden = false;
            $readonly.hidden = true;
            $input.disabled = false;
        } else {
            $form.hidden = true;
            $readonly.hidden = false;
            if (!c) {
                $readonly.textContent = '';
            } else if (c.is_closed) {
                $readonly.textContent = 'This conversation is closed.';
            } else if (c.kind === 'support' && state.isRep && !c.claimed_by_id) {
                $readonly.textContent = 'Claim this chat to reply.';
            } else if (c.kind === 'support' && state.isRep && c.claimed_by_id) {
                $readonly.textContent = 'Claimed by ' + (c.claimed_by_name || 'another rep') + '.';
            } else {
                $readonly.textContent = 'Read-only.';
            }
        }
    }

    function renderPickerResults(users) {
        $pickerResults.innerHTML = '';
        if (users.length === 0) {
            var p = document.createElement('p');
            p.className = 'chat-empty';
            p.textContent = state.pickerQuery ? 'No matches.' : 'Start typing to search.';
            $pickerResults.appendChild(p);
            return;
        }
        users.forEach(function (u) {
            var b = document.createElement('button');
            b.type = 'button';
            b.innerHTML = escapeHTML(u.name)
                + '<span class="chat-picker-role">' + escapeHTML(u.role) + '</span>';
            b.addEventListener('click', function () { pickUser(u.id); });
            $pickerResults.appendChild(b);
        });
    }

    // --- API calls -----------------------------------------------------------
    function loadState() {
        var url = '/chat/api/state/' + (state.showArchived ? '?show_archived=1' : '');
        return fetchJSON(url).then(function (data) {
            state.isRep = !!data.is_rep;
            state.isLab = !!data.is_lab;
            state.conversations = data.conversations || [];
            renderBadge(data.total_unread || 0);
            if (state.view === 'list') renderList();
            // If a conversation is open, refresh its header (claim state may
            // have changed) and reply box.
            if (state.view === 'conv' && state.activeConvId != null) {
                var c = findConv(state.activeConvId);
                state.activeConv = c;
                renderConvMeta(c);
                renderReplyBox(c);
            }
        }).catch(function (e) {
            // Silent — next poll will retry. If unauthenticated, page will
            // redirect on its next navigation.
            if (e.status === 403 || e.status === 401) stopPolling();
        });
    }

    function openConversation(id) {
        state.activeConvId = id;
        state.lastSeenMsgId = 0;
        state.activeMessages = [];
        var c = findConv(id);
        state.activeConv = c;
        $messages.innerHTML = '';
        renderConvMeta(c);
        renderReplyBox(c);
        showView('conv');
        fetchJSON('/chat/api/conversations/' + id + '/messages/')
            .then(function (data) {
                renderMessages(data.messages, false);
                return markRead(id);
            }).catch(function () {});
    }

    function pollActiveConv() {
        if (state.view !== 'conv' || state.activeConvId == null) return;
        var url = '/chat/api/conversations/' + state.activeConvId
            + '/messages/?after=' + encodeURIComponent(state.lastSeenMsgId);
        fetchJSON(url).then(function (data) {
            if (data.messages && data.messages.length) {
                renderMessages(data.messages, true);
                markRead(state.activeConvId);
            }
        }).catch(function () {});
    }

    function sendMessage() {
        var body = ($input.value || '').trim();
        if (!body || state.activeConvId == null) return;
        $input.disabled = true;
        fetchJSON('/chat/api/conversations/' + state.activeConvId + '/send/', {
            method: 'POST', body: {body: body},
        }).then(function (data) {
            $input.value = '';
            renderMessages([data.message], true);
            $input.disabled = false;
            $input.focus();
            // Refresh global state so the list reflects the new last message.
            loadState();
        }).catch(function (e) {
            $input.disabled = false;
            alert('Send failed: ' + (e.status || 'network error'));
        });
    }

    function startSupportChat() {
        // A newly started chat won't be in the archived list, so make sure
        // we're in active view before refreshing.
        state.showArchived = false;
        fetchJSON('/chat/api/conversations/start_support/', {method: 'POST', body: {}})
            .then(function (data) {
                return loadState().then(function () {
                    openConversation(data.conversation.id);
                });
            });
    }

    function pickUser(userId) {
        // start_dm reopens a closed/archived DM transparently, but the
        // archived-by set is per-user; force the active view so the user
        // can see the DM they just opened.
        state.showArchived = false;
        fetchJSON('/chat/api/conversations/start_dm/', {
            method: 'POST', body: {user_id: userId},
        }).then(function (data) {
            return loadState().then(function () {
                openConversation(data.conversation.id);
            });
        }).catch(function (e) {
            alert('Could not start DM: ' + (e.status || 'network error'));
        });
    }

    function claimChat(id) {
        fetchJSON('/chat/api/conversations/' + id + '/claim/', {method: 'POST', body: {}})
            .then(function () { return loadState(); });
    }
    function unclaimChat(id) {
        fetchJSON('/chat/api/conversations/' + id + '/unclaim/', {method: 'POST', body: {}})
            .then(function () { return loadState(); });
    }
    function closeChat(id) {
        if (!confirm('Close this conversation?')) return;
        fetchJSON('/chat/api/conversations/' + id + '/close/', {method: 'POST', body: {}})
            .then(function () { return loadState(); });
    }
    function archiveChat(id) {
        fetchJSON('/chat/api/conversations/' + id + '/archive/', {method: 'POST', body: {}})
            .then(function () {
                // Hide from the active list; bounce the user back so they can
                // see the change.
                state.activeConvId = null;
                state.activeConv = null;
                showView('list');
                return loadState();
            });
    }
    function unarchiveChat(id) {
        fetchJSON('/chat/api/conversations/' + id + '/unarchive/', {method: 'POST', body: {}})
            .then(function () {
                // The conv is now in the active list — switch the user there.
                state.showArchived = false;
                return loadState();
            });
    }
    function markRead(id) {
        return fetchJSON('/chat/api/conversations/' + id + '/read/', {method: 'POST', body: {}})
            .catch(function () {});
    }

    function searchUsers(q) {
        state.pickerQuery = q;
        var url = '/chat/api/users/' + (q ? ('?q=' + encodeURIComponent(q)) : '');
        fetchJSON(url).then(function (data) {
            renderPickerResults(data.users || []);
        });
    }

    // --- polling -------------------------------------------------------------
    function tick() {
        loadState();
        pollActiveConv();
    }
    function startPolling() {
        if (pollTimer) return;
        pollTimer = setInterval(tick, POLL_MS);
    }
    function stopPolling() {
        if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    }

    // --- init ----------------------------------------------------------------
    document.addEventListener('DOMContentLoaded', function () {
        $widget = $('chat-widget'); if (!$widget) return;
        csrf = $widget.dataset.csrf || '';

        $toggle = $('chat-toggle'); $panel = $('chat-panel');
        $badge = $('chat-badge'); $title = $('chat-title');
        $back = $('chat-back'); $close = $('chat-close');
        $viewList = $('chat-view-list'); $viewConv = $('chat-view-conv');
        $viewPicker = $('chat-view-picker');
        $list = $('chat-list'); $actions = $('chat-actions'); $empty = $('chat-empty');
        $convMeta = $('chat-conv-meta'); $messages = $('chat-messages');
        $form = $('chat-form'); $input = $('chat-input'); $readonly = $('chat-readonly');
        $pickerInput = $('chat-picker-input'); $pickerResults = $('chat-picker-results');

        $toggle.addEventListener('click', function () {
            if (isPanelOpen()) closePanel(); else openPanel();
        });
        $close.addEventListener('click', closePanel);
        $back.addEventListener('click', function () {
            state.activeConvId = null;
            state.activeConv = null;
            showView('list');
            loadState();
        });

        $form.addEventListener('submit', function (e) {
            e.preventDefault(); sendMessage();
        });
        $input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault(); sendMessage();
            }
        });

        $pickerInput.addEventListener('input', function () {
            var q = this.value.trim();
            clearTimeout(pickerTimer);
            pickerTimer = setTimeout(function () { searchUsers(q); }, 200);
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && isPanelOpen()) closePanel();
        });

        showView('list');
        try {
            if (localStorage.getItem('chat.open') === 'true') openPanel();
        } catch (e) {}

        // First load, then start polling.
        loadState();
        startPolling();
    });
})();
