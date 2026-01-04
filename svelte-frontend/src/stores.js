// Svelte 5 compatible state using stores
import { writable, derived } from 'svelte/store';

export const ws = writable(null);
export const wsConnected = writable(false);

export const rrcConnected = writable(false);
export const hubName = writable(null);
export const nickname = writable('');
export const identityHash = writable(null);
export const latency = writable(null);

export const currentRoom = writable('[Hub]');

export const rooms = writable(new Map([
    ['[Hub]', { messages: [], users: new Set(), unread: 0 }]
]));

export const discoveredHubs = writable([]);

export const connectionSettings = writable({
    hubHash: '',
    destName: 'rrc.hub',
    nickname: '',
    identityPath: '~/.rrc-web/identity'
});

// Store for tracking sent message IDs (for correlation)
export const sentMessageIds = writable(new Set());

// Derived state
export const currentRoomData = derived(
    [rooms, currentRoom],
    ([$rooms, $currentRoom]) => $rooms.get($currentRoom) || { messages: [], users: new Set(), unread: 0 }
);

export const roomList = derived(
    rooms,
    $rooms => Array.from($rooms.keys())
);
