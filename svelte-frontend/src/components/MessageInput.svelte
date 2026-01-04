<script>
    import { currentRoom } from "../stores.js";
    import { sendMessage } from "../websocket";
    import { handleCommand } from "../commands.js";

    let messageInput = $state("");

    function handleSend() {
        if (messageInput.trim()) {
            // Check if it's a command
            if (messageInput.startsWith('/')) {
                const handled = handleCommand(messageInput);
                if (handled) {
                    messageInput = "";
                    return;
                }
            }
            // Not a command or command handler returned false, send as normal message
            sendMessage(messageInput, $currentRoom);
            messageInput = "";
        }
    }

    function handleKeyPress(e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    }
</script>

<div class="p-4 bg-base-200">
    <div class="flex gap-2">
        <input
            type="text"
            bind:value={messageInput}
            onkeypress={handleKeyPress}
            placeholder="Type a message... (type /help for commands)"
            class="input input-bordered flex-1"
        />
        <button onclick={handleSend} class="btn btn-outline btn-primary p-4"> Send </button>
    </div>
</div>
