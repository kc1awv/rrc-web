<script>
    import { currentRoom, rooms, hubName, roomList as roomListStore } from "../stores.js";
    import { clearRoomUnread } from "../websocket";

    let { onJoinRoom, onPartRoom, onToggleSidebar } = $props();

    function selectRoom(room) {
        currentRoom.set(room);
        clearRoomUnread(room);
    }

    function getRoomUnread(room) {
        return $rooms.get(room)?.unread || 0;
    }

    function getRoomDisplayName(room) {
        if (room === "[Hub]") {
            return $hubName || "Hub";
        }
        return room;
    }
</script>

<div class="p-4 bg-base-200 h-full overflow-y-auto flex flex-col">
    <div class="flex justify-between items-center mb-4">
        <h3 class="font-bold text-lg">Rooms</h3>
        <button
            class="btn btn-ghost btn-sm btn-circle"
            onclick={onToggleSidebar}
            title="Collapse sidebar"
        >
            &lt;
        </button>
    </div>

    <ul class="menu-compact flex-1">
        {#each $roomListStore as room}
            <li>
                <button
                    onclick={() => selectRoom(room)}
                    class="flex justify-between items-center w-full text-left px-2 py-2 rounded {room ===
                    $currentRoom
                        ? 'bg-primary text-primary-content hover:bg-primary-focus'
                        : 'hover:bg-base-300'}"
                >
                    <span>{getRoomDisplayName(room)}</span>
                    {#if getRoomUnread(room) > 0}
                        <span class="badge badge-primary badge-sm"
                            >{getRoomUnread(room)}</span
                        >
                    {/if}
                </button>
            </li>
        {/each}
    </ul>

    <div class="divider"></div>

    <div class="flex flex-col gap-2">
        <button class="btn btn-sm btn-outline btn-success" onclick={onJoinRoom}>
            Join Room
        </button>
        {#if $currentRoom !== "[Hub]"}
            <button class="btn btn-sm btn-outline btn-warning" onclick={onPartRoom}>
                Part Room
            </button>
        {/if}
    </div>
</div>
