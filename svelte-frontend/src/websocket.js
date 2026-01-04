import { get } from 'svelte/store';
import {
    ws,
    wsConnected,
    rrcConnected,
    hubName,
    nickname,
    identityHash,
    latency,
    currentRoom,
    rooms,
    discoveredHubs,
    connectionSettings,
    sentMessageIds
} from './stores.js';

let wsInstance = null;
let pingInterval = null;
let pingTimeout = null;
let lastPingTime = null;

export function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    wsInstance = new WebSocket(wsUrl);
    ws.set(wsInstance);

    wsInstance.onopen = () => {
        wsConnected.set(true);
        requestDiscoveredHubs();
        loadConnectionSettings();
        sendWS({ type: 'get_state' });
    };

    wsInstance.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleMessage(data);
    };

    wsInstance.onerror = (error) => {
        console.error('WebSocket error:', error);
        // If we get an error during connection, it might be auth-related
        if (error.currentTarget?.readyState === WebSocket.CLOSED) {
            // Check if it's an auth error (401)
            fetch('/ws', { method: 'HEAD' })
                .then(response => {
                    if (response.status === 401) {
                        // Redirect to login or reload to show login dialog
                        window.location.reload();
                    }
                })
                .catch(() => {});
        }
    };

    wsInstance.onclose = (event) => {
        wsConnected.set(false);
        rrcConnected.set(false);
        latency.set(null);
        
        // If close code is 1008 (policy violation), it's likely auth failure
        if (event.code === 1008 || event.code === 1002) {
            console.log('WebSocket closed due to authentication failure');
            window.location.reload();
        } else {
            // Otherwise, try to reconnect
            setTimeout(connectWebSocket, 3000);
        }
    };
}

export function sendWS(data) {
    if (wsInstance && wsInstance.readyState === WebSocket.OPEN) {
        wsInstance.send(JSON.stringify(data));
    }
}

function handleMessage(data) {
    switch (data.type) {
        case 'connected':
            onConnected(data);
            break;
        case 'disconnected':
            onDisconnected();
            break;
        case 'message':
            addMessage(data);
            break;
        case 'notice':
            addNotice(data);
            break;
        case 'error':
            addError(data);
            break;
        case 'system':
            addSystemMessage(data);
            break;
        case 'message_sent':
            handleMessageSent(data);
            break;
        case 'room_joined':
            onRoomJoined(data.room, data.users);
            break;
        case 'room_parted':
            onRoomParted(data.room);
            break;
        case 'state':
            updateState(data);
            break;
        case 'latency':
            handleLatency(data);
            break;
        case 'user_list_update':
            handleUserListUpdate(data);
            break;
        case 'hub_info':
            handleHubInfo(data);
            break;
        case 'hub_discovered':
            handleHubDiscovered(data);
            break;
        case 'discovered_hubs':
            handleDiscoveredHubs(data);
            break;
        case 'nickname_set':
            handleNicknameSet(data);
            break;
    }
}

function onConnected(data) {
    rrcConnected.set(true);
    if (data.hub_name) {
        hubName.set(data.hub_name);
    }
    nickname.set(data.nickname || '');
    if (data.identity_hash) {
        identityHash.set(data.identity_hash);
    }
}

function onDisconnected() {
    rrcConnected.set(false);
    hubName.set(null);

    rooms.update(r => {
        const hub = r.get('[Hub]') || { messages: [], users: new Set(), unread: 0 };
        hub.messages.push({
            type: 'system',
            text: 'Disconnected from hub',
            timestamp: new Date().toLocaleTimeString()
        });
        r.set('[Hub]', hub);
        return new Map(r);
    });
}

function addMessage(data) {
    const room = data.room || '[Hub]';

    rooms.update(r => {
        if (!r.has(room)) {
            r.set(room, { messages: [], users: new Set(), unread: 0 });
        }

        const roomData = r.get(room);
        roomData.messages.push({
            type: 'message',
            user: data.user,
            text: data.text,
            timestamp: data.timestamp || new Date().toLocaleTimeString(),
            message_id: data.message_id,
            sender_identity: data.sender_identity
        });

        if (room !== get(currentRoom)) {
            roomData.unread++;
        }

        return new Map(r);
    });
}

function addNotice(data) {
    const room = data.room || '[Hub]';

    rooms.update(r => {
        if (!r.has(room)) {
            r.set(room, { messages: [], users: new Set(), unread: 0 });
        }

        const roomData = r.get(room);
        roomData.messages.push({
            type: 'notice',
            text: data.text,
            timestamp: data.timestamp || new Date().toLocaleTimeString()
        });

        return new Map(r);
    });
}

function addError(data) {
    const room = get(currentRoom);

    rooms.update(r => {
        const roomData = r.get(room);
        if (roomData) {
            roomData.messages.push({
                type: 'error',
                text: data.text || data.error,
                timestamp: new Date().toLocaleTimeString()
            });
        }
        return new Map(r);
    });
}

function addSystemMessage(data) {
    const room = data.room || get(currentRoom);

    rooms.update(r => {
        if (!r.has(room)) {
            r.set(room, { messages: [], users: new Set(), unread: 0 });
        }

        const roomData = r.get(room);
        roomData.messages.push({
            type: 'system',
            text: data.text,
            timestamp: data.timestamp || new Date().toLocaleTimeString()
        });

        return new Map(r);
    });
}

function handleMessageSent(data) {
    // Track the message ID of messages we sent
    if (data.message_id) {
        sentMessageIds.update(ids => {
            ids.add(data.message_id);
            // Keep set size reasonable - only track last 100 message IDs
            if (ids.size > 100) {
                const firstId = ids.values().next().value;
                ids.delete(firstId);
            }
            return ids;
        });
    }
}

function onRoomJoined(room, users) {
    rooms.update(r => {
        if (!r.has(room)) {
            r.set(room, { messages: [], users: new Set(), unread: 0 });
        }

        const roomData = r.get(room);
        roomData.users = new Set(users || []);

        return new Map(r);
    });
    currentRoom.set(room);
}

function onRoomParted(room) {
    rooms.update(r => {
        r.delete(room);
        return new Map(r);
    });

    if (get(currentRoom) === room) {
        currentRoom.set('[Hub]');
    }
}

function updateState(data) {
    if (data.connected !== undefined) {
        rrcConnected.set(data.connected);
    }

    if (data.hub_name) {
        hubName.set(data.hub_name);
    }

    if (data.nickname) {
        nickname.set(data.nickname);
    }

    if (data.identity_hash) {
        identityHash.set(data.identity_hash);
    }

    if (data.config) {
        connectionSettings.update(settings => ({
            ...settings,
            hubHash: data.config.hub_hash || settings.hubHash,
            destName: data.config.dest_name || settings.destName,
            nickname: data.config.nickname || settings.nickname,
            identityPath: data.config.identity_path || settings.identityPath
        }));
    }

    if (data.rooms && Object.keys(data.rooms).length > 0) {
        rooms.update(r => {
            const newRooms = new Map();

            Object.keys(data.rooms).forEach(roomName => {
                const serverRoom = data.rooms[roomName];
                const existingRoom = r.get(roomName);

                newRooms.set(roomName, {
                    messages: serverRoom.messages || existingRoom?.messages || [],
                    users: new Set(serverRoom.users || []),
                    unread: existingRoom?.unread || 0
                });
            });

            return newRooms;
        });
    }
}

function handleLatency(data) {
    if (data.latency_ms !== undefined) {
        latency.set(data.latency_ms);
    }
}

function handleUserListUpdate(data) {
    const room = data.room || '[Hub]';

    rooms.update(r => {
        if (!r.has(room)) {
            r.set(room, { messages: [], users: new Set(), unread: 0 });
        }

        const roomData = r.get(room);
        roomData.users = new Set(data.users || []);

        return new Map(r);
    });
}

function handleHubInfo(data) {
    hubName.set(data.hub_name);
}

function handleHubDiscovered(data) {
    if (data.hub) {
        discoveredHubs.update(hubs => {
            const exists = hubs.find(h => h.hash === data.hub.hash);
            if (!exists) {
                return [...hubs, data.hub];
            }
            return hubs;
        });
    }
}

function handleDiscoveredHubs(data) {
    discoveredHubs.set(data.hubs || []);
}

function handleNicknameSet(data) {
    if (data.nickname !== undefined) {
        nickname.set(data.nickname);
    }
}

export function requestDiscoveredHubs() {
    sendWS({ type: 'get_discovered_hubs' });
}

export function connectToHub(hubHash, destName, nick, identityPath) {
    sendWS({
        type: 'connect',
        hub_hash: hubHash,
        dest_name: destName,
        nickname: nick,
        identity_path: identityPath
    });

    saveConnectionSettings(hubHash, destName, nick, identityPath);
}

export function disconnect() {
    sendWS({ type: 'disconnect' });
}

export function joinRoom(roomName) {
    sendWS({
        type: 'join_room',
        room: roomName
    });
}

export function partRoom(roomName) {
    sendWS({
        type: 'part_room',
        room: roomName
    });
}

export function sendMessage(content, room) {
    if (!content.trim()) return;

    sendWS({
        type: 'send_message',
        text: content,
        room: room || get(currentRoom)
    });
}

export function setNickname(nick) {
    sendWS({
        type: 'set_nickname',
        nickname: nick
    });
}

function loadConnectionSettings() {
    const saved = localStorage.getItem('rrc_connection_settings');
    if (saved) {
        try {
            const settings = JSON.parse(saved);
            connectionSettings.set(settings);
        } catch (e) {
            console.error('Failed to load connection settings:', e);
        }
    }
}

function saveConnectionSettings(hubHash, destName, nick, identityPath) {
    const settings = { hubHash, destName, nickname: nick, identityPath };
    localStorage.setItem('rrc_connection_settings', JSON.stringify(settings));
    connectionSettings.set(settings);
}

export function clearRoomUnread(room) {
    rooms.update(r => {
        const roomData = r.get(room);
        if (roomData) {
            roomData.unread = 0;
        }
        return new Map(r);
    });
}
