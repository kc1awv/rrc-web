<script>
    import { joinRoom } from "../websocket";

    let { show = false, onClose } = $props();

    let roomName = $state("");

    function handleSubmit(event) {
        event.preventDefault();
        if (roomName.trim()) {
            joinRoom(roomName.trim());
            roomName = "";
            onClose();
        }
    }

    function handleCancel() {
        roomName = "";
        onClose();
    }
</script>

{#if show}
    <div class="modal modal-open">
        <div class="modal-box">
            <h3 class="font-bold text-lg">Join Room</h3>

            <form onsubmit={handleSubmit}>
                <div class="form-control mt-4">
                    <label class="label" for="roomNameInput">
                        <span class="mr-4 label-text">Room Name:</span>
                    </label>
                    <input
                        type="text"
                        id="roomNameInput"
                        bind:value={roomName}
                        class="input input-bordered"
                        placeholder="Enter room name"
                        required
                    />
                </div>

                <div class="modal-action">
                    <button type="button" class="p-4 mr-4 btn btn-error" onclick={handleCancel}>
                        Cancel
                    </button>
                    <button type="submit" class="p-4 btn btn-primary">
                        Join
                    </button>
                </div>
            </form>
        </div>
    </div>
{/if}
