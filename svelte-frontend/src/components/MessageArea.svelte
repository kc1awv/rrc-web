<script>
    import { currentRoom, currentRoomData, identityHash, sentMessageIds } from "../stores.js";

    let messageContainer;
    let shouldAutoScroll = $state(true);
    let showScrollButton = $state(false);
    let showTimestamps = $state(true);

    // Check if user is scrolled near the bottom
    function isNearBottom() {
        if (!messageContainer) return true;
        const threshold = 100; // pixels from bottom
        const scrolledToBottom = 
            messageContainer.scrollHeight - messageContainer.scrollTop - messageContainer.clientHeight <= threshold;
        return scrolledToBottom;
    }

    // Handle user scroll
    function handleScroll() {
        const nearBottom = isNearBottom();
        shouldAutoScroll = nearBottom;
        showScrollButton = !nearBottom;
    }

    // Scroll to bottom function
    function scrollToBottom() {
        if (messageContainer) {
            messageContainer.scrollTop = messageContainer.scrollHeight;
            shouldAutoScroll = true;
            showScrollButton = false;
        }
    }

    // Auto-scroll effect when messages change
    $effect(() => {
        // Explicitly track messages to trigger on changes
        const messages = $currentRoomData?.messages;
        
        if (messageContainer && shouldAutoScroll && messages) {
            // Use requestAnimationFrame to ensure DOM is fully updated
            requestAnimationFrame(() => {
                if (messageContainer && shouldAutoScroll) {
                    messageContainer.scrollTop = messageContainer.scrollHeight;
                }
            });
        }
    });

    // Reset auto-scroll when switching rooms
    $effect(() => {
        const roomId = $currentRoomData?.room_id;
        // When room changes, reset to auto-scroll mode
        shouldAutoScroll = true;
        showScrollButton = false;
    });

    function isOwnMessage(msg) {
        // Check if this is our own message by comparing:
        // 1. Message ID is in our sent messages set, AND
        // 2. Sender identity matches our identity hash
        if (msg.type === "message" && 
            msg.message_id && 
            msg.sender_identity && 
            $identityHash &&
            $sentMessageIds && 
            $sentMessageIds.has(msg.message_id) && 
            msg.sender_identity === $identityHash) {
            return true;
        }
        return false;
    }

    function getMessageText(msg) {
        switch (msg.type) {
            case "join":
                return `→ ${msg.user} joined`;
            case "part":
                return `← ${msg.user} left`;
            case "notice":
                return formatNotice(msg.text);
            default:
                return msg.text;
        }
    }
    
    function formatNotice(text) {
        if (!text) return text;
        
        // Parse IRC-style room notice: "room test: registered; mode=+nrt; topic=this is a test room"
        const match = text.match(/^room\s+(\S+):\s*registered;\s*mode=([^;]+);\s*topic=(.+)$/);
        if (match) {
            const [, roomName, mode, topic] = match;
            return topic ? `Topic: ${topic}` : `Room ${roomName} registered`;
        }
        
        // If it doesn't match the expected format, return as-is
        return text;
    }
</script>

<div class="message-area-wrapper">
    {#if $currentRoom !== '[Hub]'}
        <div class="flex justify-end p-2 border-b border-base-300">
            <label class="label cursor-pointer gap-2">
                <span class="label-text text-xs">Show timestamps</span>
                <input type="checkbox" class="toggle toggle-sm" bind:checked={showTimestamps} />
            </label>
        </div>
    {/if}
    <div bind:this={messageContainer} class="message-area p-4" onscroll={handleScroll}>
        {#each ($currentRoomData?.messages || []) as msg, index (msg.timestamp + (msg.text || msg.type || '') + (msg.user || '') + index)}
            {#if msg.type === 'join' || msg.type === 'part' || msg.type === 'notice' || msg.type === 'system' || msg.type === 'error'}
                <!-- Join/Part/Notice/System/Error informational messages -->
                <div class="my-2">
                    {#if showTimestamps || $currentRoom === '[Hub]'}
                        <span class="text-xs opacity-40 mr-2">{msg.timestamp}</span>
                    {/if}
                    <span class="text-sm opacity-60 {msg.type === 'join' ? 'text-success' : msg.type === 'part' ? 'text-warning' : msg.type === 'error' ? 'text-error' : 'text-info'}" style="white-space: pre-line;">
                        {getMessageText(msg)}
                    </span>
                </div>
            {:else if msg.type === 'message'}
                <!-- Regular chat messages -->
                <div class="my-1">
                    {#if showTimestamps || $currentRoom === '[Hub]'}
                        <span class="text-xs opacity-40 mr-2">{msg.timestamp}</span>
                    {/if}
                    <span class="font-semibold {isOwnMessage(msg) ? 'text-accent' : 'text-primary'}">{msg.user}</span>
                    <span class="ml-2" style="white-space: pre-line;">{msg.text}</span>
                </div>
            {/if}
        {/each}
    </div>

    {#if showScrollButton}
        <button
            class="scroll-to-bottom-btn btn btn-circle btn-primary btn-sm"
            onclick={scrollToBottom}
            aria-label="Scroll to bottom"
        >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
        </button>
    {/if}
</div>

<style>
    .message-area-wrapper {
        position: relative;
        flex: 1;
        min-height: 0;
        display: flex;
        flex-direction: column;
    }

    .scroll-to-bottom-btn {
        position: absolute;
        bottom: 1rem;
        right: 1rem;
        z-index: 10;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }

    .scroll-to-bottom-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 8px -1px rgba(0, 0, 0, 0.15), 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
</style>