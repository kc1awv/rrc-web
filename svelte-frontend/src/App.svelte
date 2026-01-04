<script>
    import { rrcConnected, currentRoom } from "./stores.js";
    import { partRoom } from "./websocket";

    import Navbar from "./components/Navbar.svelte";
    import ConnectionDialog from "./components/ConnectionDialog.svelte";
    import RoomSidebar from "./components/RoomSidebar.svelte";
    import MessageArea from "./components/MessageArea.svelte";
    import MessageInput from "./components/MessageInput.svelte";
    import UserList from "./components/UserList.svelte";
    import JoinRoomDialog from "./components/JoinRoomDialog.svelte";
    import MobileMenu from "./components/MobileMenu.svelte";

    let showJoinRoomDialog = $state(false);
    let sidebarCollapsed = $state(false);
    let mobileMenuOpen = $state(false);

    function handleConnect() {
        // Connection dialog will close when we get connected event
    }

    function handleJoinRoom() {
        showJoinRoomDialog = true;
    }

    function handlePartRoom() {
        const room = $currentRoom;
        if (room !== "[Hub]") {
            partRoom(room);
        }
    }

    function handleCloseJoinDialog() {
        showJoinRoomDialog = false;
    }

    function handleToggleTheme(theme) {
        // You can handle theme changes here if needed
    }

    function toggleSidebar() {
        sidebarCollapsed = !sidebarCollapsed;
    }

    function toggleMobileMenu() {
        mobileMenuOpen = !mobileMenuOpen;
    }

    function closeMobileMenu() {
        mobileMenuOpen = false;
    }
</script>

<!-- Desktop Layout -->
<div class="hidden md:flex md:flex-col h-full">
    <!-- Full-width Navbar -->
    <Navbar onToggleTheme={handleToggleTheme} />

    <!-- Main content with sidebar -->
    <div class="flex flex-1 min-h-0">
        <!-- Collapsible Sidebar -->
        {#if !sidebarCollapsed}
            <div class="w-64 border-r border-base-300 flex-shrink-0">
                <RoomSidebar
                    onJoinRoom={handleJoinRoom}
                    onPartRoom={handlePartRoom}
                    onToggleSidebar={toggleSidebar}
                />
            </div>
        {:else}
            <!-- Collapsed sidebar - show expand button -->
            <div class="border-r border-base-300 flex-shrink-0 bg-base-200">
                <button
                    class="btn btn-ghost btn-sm m-2"
                    onclick={toggleSidebar}
                    title="Expand sidebar"
                >
                    &gt;
                </button>
            </div>
        {/if}

        <!-- Messages and User List -->
        <div class="flex-1 flex min-h-0">
            <div class="flex-1 flex flex-col min-h-0">
                <MessageArea />
                <MessageInput />
            </div>

            <!-- User list -->
            <div
                class="hidden xl:block w-64 border-l border-base-300 overflow-y-auto flex-shrink-0"
            >
                <UserList />
            </div>
        </div>
    </div>
</div>

<!-- Mobile Layout -->
<div class="md:hidden flex flex-col h-full">
    <!-- Mobile Navbar with hamburger -->
    <div class="navbar bg-base-300">
        <div class="flex-none">
            <button
                class="btn btn-square btn-ghost"
                onclick={toggleMobileMenu}
                aria-label="Toggle mobile menu"
            >
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    class="inline-block w-5 h-5 stroke-current"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M4 6h16M4 12h16M4 18h16"
                    ></path>
                </svg>
            </button>
        </div>

        <div class="flex-1 px-2">
            <span class="text-lg font-bold">RRC</span>
            <span class="ml-2 text-sm opacity-70">- {$currentRoom}</span>
        </div>
    </div>

    <!-- Mobile Menu Drawer -->
    <MobileMenu
        isOpen={mobileMenuOpen}
        onClose={closeMobileMenu}
        onToggleTheme={handleToggleTheme}
        onJoinRoom={handleJoinRoom}
        onPartRoom={handlePartRoom}
    />

    <!-- Messages -->
    <div class="flex-1 flex flex-col min-h-0">
        <MessageArea />
        <MessageInput />
    </div>
</div>

<!-- Modals -->
{#if !$rrcConnected}
    <ConnectionDialog onConnect={handleConnect} />
{/if}

<JoinRoomDialog show={showJoinRoomDialog} onClose={handleCloseJoinDialog} />
