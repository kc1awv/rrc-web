// Svelte 5 runes-based stores

export let ws = $state(null);
export let wsConnected = $state(false);

export let rrcConnected = $state(false);
export let hubName = $state(null);
export let nickname = $state('');
export let latency = $state(null);

export let currentRoom = $state('[Hub]');

export let rooms = $state(new Map([
    ['[Hub]', { messages: [], users: new Set(), unread: 0 }]
]));

export let discoveredHubs = $state([]);

export let connectionSettings = $state({
    hubHash: '',
    destName: 'rrc.hub',
    nickname: '',
    identityPath: '~/.rrc-web/identity'
});

// Derived state accessors (functions that return the current value)
export function getCurrentRoomData() {
    return rooms.get(currentRoom) || { messages: [], users: new Set(), unread: 0 };
}

export function getRoomList() {
    return Array.from(rooms.keys());
}
