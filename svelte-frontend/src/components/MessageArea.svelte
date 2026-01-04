<script>
    import { currentRoomData, identityHash, sentMessageIds } from "../stores.js";

    let messageContainer;

    $effect(() => {
        if (messageContainer) {
            messageContainer.scrollTop = messageContainer.scrollHeight;
        }
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

<div bind:this={messageContainer} class="message-area p-4">
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
