<script>
    import { currentRoomData } from "../stores.js";
</script>

<div class="p-4 bg-base-200 h-full overflow-y-auto">
    <h3 class="font-bold text-lg mb-4">Users</h3>

    {#if $currentRoomData.users.size === 0}
        <p class="text-sm opacity-60">No users</p>
    {:else}
        <ul class="menu menu-compact">
            {#each Array.from($currentRoomData.users) as user}
                <li>
                    <span class="text-sm">{user}</span>
                </li>
            {/each}
        </ul>
    {/if}
</div>
