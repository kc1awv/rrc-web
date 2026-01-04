<script>
    let token = $state("");
    let error = $state("");
    let loading = $state(false);
    
    // Detect theme preference
    let isDarkTheme = $state(true);
    
    $effect(() => {
        // Check data-theme attribute on html element
        const htmlTheme = document.documentElement.getAttribute('data-theme');
        if (htmlTheme) {
            isDarkTheme = htmlTheme === 'dark';
        } else {
            // Fall back to system preference
            isDarkTheme = window.matchMedia('(prefers-color-scheme: dark)').matches;
        }
        
        // Listen for theme changes
        const observer = new MutationObserver(() => {
            const theme = document.documentElement.getAttribute('data-theme');
            if (theme) {
                isDarkTheme = theme === 'dark';
            }
        });
        
        observer.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ['data-theme']
        });
        
        return () => observer.disconnect();
    });

    async function handleLogin() {
        error = "";
        loading = true;

        try {
            const response = await fetch("/api/login", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ token }),
            });

            const data = await response.json();

            if (response.ok) {
                // Login successful, reload to establish WebSocket connection
                window.location.reload();
            } else {
                error = data.error || "Login failed";
            }
        } catch (err) {
            error = "Failed to connect to server";
            console.error("Login error:", err);
        } finally {
            loading = false;
        }
    }

    function handleKeydown(event) {
        if (event.key === "Enter" && !loading) {
            handleLogin();
        }
    }
</script>

<div class="hero min-h-screen bg-base-200">
    <div class="hero-content flex-col">
        <div class="text-center lg:text-left mb-8">
            <img 
                src={isDarkTheme ? "/transparent-logo-dark.png" : "/transparent-logo-light.png"} 
                alt="RRC Logo" 
                class="w-64 mx-auto" 
            />
            <p>
                Authentication has been enabled on this application.
            </p>
            <p>
                Please enter your authentication token to continue.
            </p>
        </div>
        <div class="card flex-shrink-0 w-full max-w-sm shadow-2xl bg-base-100">
            <div class="card-body">
                <div class="form-control">
                    <label class="label" for="token-input">
                        <span class="label-text">Authentication Token</span>
                    </label>
                    <input
                        id="token-input"
                        type="password"
                        placeholder="Enter your token"
                        class="input input-bordered"
                        bind:value={token}
                        onkeydown={handleKeydown}
                        disabled={loading}
                        autocomplete="off"
                    />
                    {#if error}
                        <div class="label">
                            <span class="label-text-alt text-error">{error}</span>
                        </div>
                    {/if}
                </div>
                <div class="form-control mt-6">
                    <button
                        class="btn btn-primary"
                        onclick={handleLogin}
                        disabled={loading || !token.trim()}
                    >
                        {#if loading}
                            <span class="loading loading-spinner"></span>
                            Authenticating...
                        {:else}
                            Login
                        {/if}
                    </button>
                </div>
                <div class="divider"></div>
                <div class="text-sm opacity-70">
                    <p class="mb-2">To generate a token, run:</p>
                    <code class="block bg-base-300 p-2 rounded text-xs overflow-x-auto">
                        python -c "import secrets; print(secrets.token_urlsafe(32))"
                    </code>
                    <p class="mt-2">
                        Add the token to your <code>config.json</code> file.
                    </p>
                </div>
            </div>
        </div>
    </div>
</div>
