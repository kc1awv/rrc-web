<script>
    import { wsConnected, rrcConnected, hubName, nickname, latency, currentRoom, rooms, roomList as roomListStore } from "../stores.js";
    import { disconnect, clearRoomUnread } from "../websocket";

    let { isOpen = false, onClose, onToggleTheme, onJoinRoom, onPartRoom } = $props();

    let theme = $state("dark");

    function toggleTheme() {
        theme = theme === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", theme);
        onToggleTheme(theme);
    }

    function handleDisconnect() {
        disconnect();
        onClose();
    }

    function selectRoom(room) {
        currentRoom.set(room);
        clearRoomUnread(room);
        onClose();
    }

    function getRoomUnread(room) {
        return $rooms.get(room)?.unread || 0;
    }

    function handleJoinRoom() {
        onJoinRoom();
        onClose();
    }

    function handlePartRoom() {
        onPartRoom();
        onClose();
    }
</script>

{#if isOpen}
    <div class="fixed inset-0 z-50 flex">
        <!-- Overlay -->
        <div class="fixed inset-0 bg-black/50" onclick={onClose} onkeydown={(e) => e.key === 'Enter' && onClose()} role="button" tabindex="0"></div>

        <!-- Menu -->
        <div class="relative w-80 bg-base-200 h-full overflow-y-auto shadow-xl">
            <div class="p-4">
                <!-- Close button -->
                <div class="flex justify-between items-center mb-4">
                    <h2 class="text-xl font-bold">Menu</h2>
                    <button
                        class="btn btn-ghost btn-sm btn-circle"
                        onclick={onClose}>✕</button
                    >
                </div>

                <!-- Connection Status -->
                <div class="card bg-base-300 mb-4">
                    <div class="card-body p-3">
                        <h3 class="font-semibold text-sm mb-2">Status</h3>
                        <div class="flex flex-col gap-2 text-sm">
                            <div class="flex items-center gap-2">
                                <div
                                    class="badge {$wsConnected
                                        ? 'badge-success'
                                        : 'badge-error'} badge-xs"
                                ></div>
                                <span
                                    >WebSocket: {$wsConnected
                                        ? "Connected"
                                        : "Disconnected"}</span
                                >
                            </div>
                            <div class="flex items-center gap-2">
                                <div
                                    class="badge {$rrcConnected
                                        ? 'badge-success'
                                        : 'badge-error'} badge-xs"
                                ></div>
                                <span
                                    >RRC: {$rrcConnected
                                        ? "Connected"
                                        : "Disconnected"}</span
                                >
                            </div>
                            {#if $hubName}
                                <div class="flex items-center gap-2">
                                    <span class="opacity-70">Hub:</span>
                                    <span>{$hubName}</span>
                                </div>
                            {/if}
                            {#if $nickname}
                                <div class="flex items-center gap-2">
                                    <span class="opacity-70">Nickname:</span>
                                    <span>{$nickname}</span>
                                </div>
                            {/if}
                            {#if $latency !== null}
                                <div class="flex items-center gap-2">
                                    <span class="opacity-70">Latency:</span>
                                    <span>{$latency}ms</span>
                                </div>
                            {/if}
                        </div>
                    </div>
                </div>

                <!-- Actions -->
                <div class="flex flex-col gap-2 mb-4">
                    <button
                        class="btn btn-sm btn-ghost justify-start"
                        onclick={toggleTheme}
                    >
                        {#if theme === "dark"}
                            ☀️ Light Mode
                        {:else}
                            🌙 Dark Mode
                        {/if}
                    </button>
                    {#if $rrcConnected}
                        <button
                            class="btn btn-sm btn-error justify-start"
                            onclick={handleDisconnect}
                        >
                            Disconnect
                        </button>
                    {/if}
                </div>

                <div class="divider"></div>

                <!-- Rooms -->
                <h3 class="font-bold text-lg mb-2">Rooms</h3>
                <ul class="menu menu-compact mb-4">
                    {#each $roomListStore as room}
                        <li>
                            <button
                                onclick={() => selectRoom(room)}
                                class="flex justify-between items-center {room ===
                                $currentRoom
                                    ? 'active'
                                    : ''}"
                            >
                                <span>{room}</span>
                                {#if getRoomUnread(room) > 0}
                                    <span class="badge badge-primary badge-sm"
                                        >{getRoomUnread(room)}</span
                                    >
                                {/if}
                            </button>
                        </li>
                    {/each}
                </ul>

                <div class="flex flex-col gap-2">
                    <button
                        class="btn btn-sm btn-outline btn-primary"
                        onclick={handleJoinRoom}
                    >
                        Join Room
                    </button>
                    {#if $currentRoom !== "[Hub]"}
                        <button
                            class="btn btn-sm btn-outline btn-warning"
                            onclick={handlePartRoom}
                        >
                            Part Room
                        </button>
                    {/if}
                </div>
            </div>
        </div>
    </div>
{/if}
