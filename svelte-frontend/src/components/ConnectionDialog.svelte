<script>
    import { onMount } from "svelte";
    import { discoveredHubs, connectionSettings } from "../stores.js";
    import { connectToHub, requestDiscoveredHubs } from "../websocket";

    let { onConnect } = $props();

    let hubHash = $state($connectionSettings.hubHash);
    let destName = $state($connectionSettings.destName);
    let nick = $state($connectionSettings.nickname);
    let identityPath = $state($connectionSettings.identityPath);
    let showAdvanced = $state(false);

    // React to changes in connectionSettings store
    $effect(() => {
        hubHash = $connectionSettings.hubHash || hubHash;
        destName = $connectionSettings.destName || destName;
        nick = $connectionSettings.nickname || nick;
        identityPath = $connectionSettings.identityPath || identityPath;
    });

    onMount(() => {
        // Request discovered hubs when dialog opens
        requestDiscoveredHubs();
    });

    function handleSubmit() {
        connectToHub(hubHash, destName, nick, identityPath);
        onConnect();
    }

    function selectHub(hub) {
        hubHash = hub.hash;
        destName = hub.aspect || "rrc.hub";
    }

    function refresh() {
        requestDiscoveredHubs();
    }

    function formatTimeAgo(lastSeen) {
        const now = Date.now() / 1000; // Convert to seconds
        const secondsAgo = Math.floor(now - lastSeen);

        if (secondsAgo < 60) {
            return `${secondsAgo}s ago`;
        } else if (secondsAgo < 3600) {
            return `${Math.floor(secondsAgo / 60)}m ago`;
        } else {
            return `${Math.floor(secondsAgo / 3600)}h ago`;
        }
    }
</script>

<div class="modal modal-open">
    <div class="modal-box max-w-6xl">
        <h3 class="font-bold text-lg mb-4">Connect to RRC Hub</h3>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <!-- Discovered Hubs -->
            <div class="card bg-base-200">
                <div class="card-body">
                    <div class="flex justify-between items-center mb-2">
                        <h4 class="card-title text-base">
                            Discovered Hubs
                            {#if $discoveredHubs.length > 0}
                                <span class="badge badge-sm">{$discoveredHubs.length}</span>
                            {/if}
                        </h4>
                        <button
                            class="btn btn-ghost btn-sm btn-circle"
                            onclick={refresh}
                            title="Refresh"
                        >
                            ↻
                        </button>
                    </div>

                    <div class="overflow-y-auto max-h-64">
                        {#if $discoveredHubs.length === 0}
                            <div class="text-center py-8">
                                <p class="text-base-content/60 text-sm mb-2">
                                    No hubs discovered yet
                                </p>
                                <p class="text-base-content/40 text-xs">
                                    Listening for announcements...
                                </p>
                            </div>
                        {:else}
                            <ul class="menu menu-sm">
                                {#each $discoveredHubs as hub}
                                    <li>
                                        <button
                                            onclick={() => selectHub(hub)}
                                            class="text-left"
                                        >
                                            <div class="w-full">
                                                <div class="font-semibold">
                                                    {hub.name || "Unknown Hub"}
                                                </div>
                                                <div
                                                    class="flex justify-between items-center text-xs opacity-60"
                                                >
                                                    <span
                                                        >{hub.hash?.substring(
                                                            0,
                                                            16,
                                                        )}...</span
                                                    >
                                                    {#if hub.last_seen}
                                                        <span class="ml-2"
                                                            >{formatTimeAgo(
                                                                hub.last_seen,
                                                            )}</span
                                                        >
                                                    {/if}
                                                </div>
                                            </div>
                                        </button>
                                    </li>
                                {/each}
                            </ul>
                        {/if}
                    </div>
                </div>
            </div>

            <!-- Connection Form -->
            <div class="card bg-base-200">
                <div class="card-body">
                    <h4 class="card-title text-base mb-2">
                        Connection Details
                    </h4>

                    <form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="space-y-3">
                        <div class="form-control w-full">
                            <label class="label" for="hubHash">
                                <span class="label-text">Hub Hash:</span>
                            </label>
                            <input
                                type="text"
                                id="hubHash"
                                bind:value={hubHash}
                                class="input input-bordered input-sm w-full mb-2"
                                placeholder="destination hash"
                                required
                            />
                            <div class="label">
                                <span class="label-text-alt"
                                    >Select a discovered hub or enter manually</span
                                >
                            </div>
                        </div>

                        <div class="form-control w-full">
                            <label class="label" for="nickname">
                                <span class="label-text">Nickname:</span>
                            </label>
                            <input
                                type="text"
                                id="nickname"
                                bind:value={nick}
                                class="input input-bordered input-sm w-full mb-2"
                                placeholder="optional"
                            />
                        </div>

                        <div class="collapse collapse-arrow bg-base-100 mt-2">
                            <input
                                type="checkbox"
                                bind:checked={showAdvanced}
                            />
                            <div class="collapse-title text-sm font-medium">
                                Advanced Options
                            </div>
                            <div class="collapse-content space-y-3">
                                <div class="form-control w-full">
                                    <label class="label" for="destName">
                                        <span class="label-text"
                                            >Destination Aspect</span
                                        >
                                    </label>
                                    <input
                                        type="text"
                                        id="destName"
                                        bind:value={destName}
                                        class="input input-bordered input-sm w-full"
                                    />
                                    <label class="label" for="destName">
                                        <span class="label-text-alt"
                                            >RNS aspect filter</span
                                        >
                                    </label>
                                </div>

                                <div class="form-control w-full">
                                    <label class="label" for="identityPath">
                                        <span class="label-text"
                                            >Identity Path</span
                                        >
                                    </label>
                                    <input
                                        type="text"
                                        id="identityPath"
                                        bind:value={identityPath}
                                        class="input input-bordered input-sm w-full"
                                    />
                                </div>
                            </div>
                        </div>

                        <div class="card-actions justify-end mt-4">
                            <button
                                type="submit"
                                class="btn btn-primary p-4"
                            >
                                Connect
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
