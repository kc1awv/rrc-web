<script>
    import { wsConnected, rrcConnected, hubName, nickname, latency, currentRoom } from "../stores.js";
    import { disconnect } from "../websocket";

    let { onToggleTheme } = $props();

    let theme = $state("dark");

    function toggleTheme() {
        theme = theme === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", theme);
        onToggleTheme(theme);
    }

    function handleDisconnect() {
        disconnect();
    }

    async function handleLogout() {
        try {
            await fetch("/api/logout", { method: "POST" });
            // Reload page to show login dialog
            window.location.reload();
        } catch (error) {
            console.error("Logout error:", error);
            // Still reload even if logout request fails
            window.location.reload();
        }
    }

    function getRoomDisplayName(room) {
        if (room === "[Hub]") {
            return $hubName || "Hub";
        }
        return room;
    }
</script>

<div class="navbar bg-base-300">
    <div class="flex-1 px-4 flex items-center gap-2">
        <img src="/transparent-icon.png" alt="RRC" class="h-8 w-8" />
        <span class="text-xl font-bold">RRC Web Client</span>
        {#if $hubName}
            <span class="text-sm opacity-70">- {$hubName}</span>
        {/if}

        <!-- Disconnect button -->
        {#if $rrcConnected}
            <button class="btn btn-outline btn-error btn-sm" onclick={handleDisconnect}>
                Disconnect
            </button>
        {/if}
    </div>

    <div class="flex-none">
        <div class="flex items-center gap-3">
            <!-- Status indicators -->
            <div class="flex items-center gap-3 text-sm">
                {#if $wsConnected}
                    <div class="flex items-center gap-1">
                        <div class="badge badge-success badge-xs"></div>
                        <span>WS</span>
                    </div>
                {:else}
                    <div class="flex items-center gap-1">
                        <div class="badge badge-error badge-xs"></div>
                        <span>WS</span>
                    </div>
                {/if}

                {#if $rrcConnected}
                    <div class="flex items-center gap-1">
                        <div class="badge badge-success badge-xs"></div>
                        <span>RRC</span>
                    </div>
                {:else}
                    <div class="flex items-center gap-1">
                        <div class="badge badge-error badge-xs"></div>
                        <span>RRC</span>
                    </div>
                {/if}

                {#if $nickname}
                    <div class="flex items-center gap-1">
                        <span class="opacity-70">Nick:</span>
                        <span>{$nickname}</span>
                    </div>
                {/if}

                {#if $latency !== null}
                    <div class="flex items-center gap-1">
                        <span class="opacity-70">Latency:</span>
                        <span>{$latency}ms</span>
                    </div>
                {/if}
            </div>

            <!-- Current room display -->
            <div class="badge badge-lg badge-primary">
                {getRoomDisplayName($currentRoom)}
            </div>

            <!-- Theme toggle -->
            <button
                class="btn btn-ghost btn-circle btn-sm"
                onclick={toggleTheme}
                title="Toggle theme"
            >
                {#if theme === "dark"}
                    ☀️
                {:else}
                    🌙
                {/if}
            </button>

            <!-- Logout button (only show if auth is enabled) -->
            <button
                class="btn btn-ghost btn-sm"
                onclick={handleLogout}
                title="Logout"
            >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
                </svg>
            </button>
        </div>
    </div>
</div>
