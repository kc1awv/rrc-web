<script>
    import { currentRoomData, identityHash, sentMessageIds } from "../stores.js";

    let messageContainer;
    let shouldAutoScroll = $state(true);
    let showScrollButton = $state(false);

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

    function getMessageClass(msg) {
        if (isOwnMessage(msg)) {
            return "chat chat-end";
        }
        
        switch (msg.type) {
            case "message":
                return "chat chat-start";
            case "system":
                return "chat chat-end";
            case "notice":
                return "chat chat-end";
            case "error":
                return "chat chat-end";
            default:
                return "chat";
        }
    }

    function getBubbleClass(msg) {
        if (isOwnMessage(msg)) {
            return "chat-bubble chat-bubble-accent";
        }
        
        switch (msg.type) {
            case "message":
                return "chat-bubble chat-bubble-primary";
            case "system":
                return "chat-bubble chat-bubble-info";
            case "notice":
                return "chat-bubble chat-bubble-warning";
            case "error":
                return "chat-bubble chat-bubble-error";
            default:
                return "chat-bubble";
        }
    }
</script>

<div class="message-area-wrapper">
    <div bind:this={messageContainer} class="message-area p-4" onscroll={handleScroll}>
        {#each ($currentRoomData?.messages || []) as msg, index (msg.timestamp + msg.text + index)}
            <div class={getMessageClass(msg)}>
                {#if msg.user}
                    <div class="chat-header">
                        {msg.user}
                        <time class="text-xs opacity-50">{msg.timestamp}</time>
                    </div>
                {/if}
                <div class={getBubbleClass(msg)} style="white-space: pre-line;">
                    {msg.text}
                </div>
                {#if !msg.user && msg.timestamp}
                    <div class="chat-footer opacity-50">
                        <time class="text-xs">{msg.timestamp}</time>
                    </div>
                {/if}
            </div>
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