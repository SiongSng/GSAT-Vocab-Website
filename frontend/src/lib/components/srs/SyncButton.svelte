<script lang="ts">
    import { getAuthStore } from "$lib/stores/auth.svelte";
    import { getSyncStore } from "$lib/stores/sync.svelte";

    const auth = getAuthStore();
    const sync = getSyncStore();

    let showConflictDialog = $state(false);
    let showErrorPopover = $state(false);
    let conflictData = $state<{ cloudTime: number; localTime: number } | null>(
        null,
    );

    const STALE_THRESHOLD = 24 * 60 * 60 * 1000; // 24 hours
    const isStale = $derived(
        auth.user && Date.now() - sync.lastSyncTime > STALE_THRESHOLD,
    );

    async function handleSync() {
        if (sync.status === "syncing") return;

        // If already in error state, clicking shows the popover
        if (sync.status === "error" && !showErrorPopover) {
            showErrorPopover = true;
            return;
        }

        showErrorPopover = false;
        if (!auth.user) {
            try {
                await auth.login({ method: "redirect" });
            } catch (e) {
                return;
            }

            if (!auth.user) return;
        }

        try {
            const result = await sync.syncWithCloud();
            if (result?.conflict) {
                conflictData = {
                    cloudTime: result.cloudTime,
                    localTime: result.localTime,
                };
                showConflictDialog = true;
            } else if (result?.rateLimited || sync.status === "error") {
                showErrorPopover = true;
            }
        } catch (e) {
            console.error("Sync error:", e);
            showErrorPopover = true;
        }
    }

    async function resolveConflict(overwriteLocal: boolean) {
        showConflictDialog = false;
        if (overwriteLocal) {
            await sync.syncWithCloud(true);
        }
    }

    function formatDate(ts: number) {
        if (!ts) return "從未同步";
        return new Date(ts).toLocaleString("zh-TW", {
            month: "numeric",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    }
</script>

<div class="flex items-center gap-2 relative">
    {#if auth.user}
        <div
            class="hidden sm:flex items-center gap-2 px-2 py-1 rounded-full bg-surface-secondary border border-border"
        >
            {#if auth.user.photoURL}
                <img
                    src={auth.user.photoURL}
                    alt="Avatar"
                    class="w-5 h-5 rounded-full border border-border"
                />
            {/if}
            <span
                class="text-[11px] font-medium text-content-secondary truncate max-w-20"
                >{auth.user.displayName || "使用者"}</span
            >
            <button
                onclick={() => auth.logout()}
                class="p-1 rounded-full hover:bg-srs-again/10 text-content-tertiary hover:text-srs-again transition-colors"
                title="登出"
            >
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="10"
                    height="10"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2.5"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    ><path
                        d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"
                    /><polyline points="16 17 21 12 16 7" /><line
                        x1="21"
                        y1="12"
                        x2="9"
                        y2="12"
                    /></svg
                >
            </button>
        </div>
    {/if}

    <div class="relative">
        <button
            onclick={handleSync}
            disabled={sync.status === "syncing"}
            class="mode-btn p-2 rounded-lg transition-all relative group flex items-center gap-1.5"
            class:active={sync.status === "syncing"}
            title={auth.user
                ? `立即同步 (上次同步: ${formatDate(sync.lastSyncTime)})`
                : "登入 Google 以同步"}
        >
            {#if sync.status === "syncing"}
                <div
                    class="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin"
                ></div>
            {:else if auth.user}
                <!-- Traffic light status dot -->
                <div
                    class="w-1.5 h-1.5 rounded-full transition-colors shadow-sm"
                    class:bg-srs-good={!isStale && sync.status !== "error"}
                    class:bg-srs-hard={isStale && sync.status !== "error"}
                    class:bg-srs-again={sync.status === "error"}
                ></div>

                <!-- Sync icon -->
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="w-4 h-4 text-content-tertiary group-hover:text-content-secondary transition-colors"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true"
                    focusable="false"
                >
                    <path
                        d="M20 12a8 8 0 1 1-8-8c2.24 0 4.38.89 5.99 2.44L20 8"
                    />
                    <path d="M20 3v5h-5" />
                </svg>
            {:else}
                <!-- Login icon -->
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="w-5 h-5 text-content-tertiary"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.5"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true"
                    focusable="false"
                >
                    <path d="M12 13v8" />
                    <path d="m15 16-3-3-3 3" />
                    <path
                        d="M20 16.2A4.5 4.5 0 0 0 17.5 8h-1.8A7 7 0 1 0 4 14.9"
                    />
                </svg>
            {/if}
        </button>

        {#if sync.status === "error" && showErrorPopover}
            <div class="error-popover">
                <div class="popover-header">
                    <h4 class="popover-title">
                        {sync.lastSyncError?.includes("頻繁")
                            ? "同步冷卻中"
                            : "同步發生錯誤"}
                    </h4>
                    <button
                        type="button"
                        class="popover-close"
                        onclick={() => (showErrorPopover = false)}
                        aria-label="關閉"
                    >
                        <svg
                            class="w-4 h-4"
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke-width="1.5"
                            stroke="currentColor"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M6 18 18 6M6 6l12 12"
                            />
                        </svg>
                    </button>
                </div>
                <p class="popover-desc">
                    {sync.lastSyncError ||
                        "連線至雲端時發生問題，請檢查網路狀態或稍後再試。"}
                </p>
            </div>
        {/if}
    </div>
</div>

{#if showConflictDialog && conflictData}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div
        class="modal-backdrop"
        onclick={() => (showConflictDialog = false)}
        role="presentation"
    >
        <div
            class="modal-container"
            onclick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            tabindex="-1"
        >
            <div class="modal-header">
                <button
                    type="button"
                    class="close-btn"
                    onclick={() => (showConflictDialog = false)}
                    aria-label="關閉"
                >
                    <svg
                        class="w-5 h-5"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke-width="1.5"
                        stroke="currentColor"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M6 18 18 6M6 6l12 12"
                        />
                    </svg>
                </button>
            </div>

            <div class="modal-content">
                <header class="mb-5">
                    <h2
                        class="text-xl font-semibold tracking-tight text-content-primary mb-2"
                    >
                        同步衝突
                    </h2>
                    <p class="text-sm text-content-secondary leading-relaxed">
                        雲端與本機的資料不一致，請選擇要保留的版本。
                    </p>
                </header>

                <div class="conflict-options">
                    <button
                        type="button"
                        onclick={() => resolveConflict(true)}
                        class="conflict-option"
                    >
                        <div class="option-row">
                            <span class="option-label">雲端版本</span>
                            <span class="option-badge">較新</span>
                        </div>
                        <p class="option-time">
                            {formatDate(conflictData.cloudTime)}
                        </p>
                        <p class="option-desc">覆蓋本機進度</p>
                    </button>

                    <button
                        type="button"
                        onclick={() => (showConflictDialog = false)}
                        class="conflict-option conflict-option-alt"
                    >
                        <div class="option-row">
                            <span class="option-label">本機版本</span>
                        </div>
                        <p class="option-time">
                            {formatDate(conflictData.localTime)}
                        </p>
                        <p class="option-desc">保留目前進度，稍後同步</p>
                    </button>
                </div>
            </div>
        </div>
    </div>
{/if}

<style>
    .bg-srs-again {
        background-color: var(--color-srs-again);
    }
    .bg-srs-good {
        background-color: var(--color-srs-good);
    }
    .bg-srs-hard {
        background-color: var(--color-srs-hard);
    }

    .mode-btn {
        color: var(--color-content-tertiary);
    }
    .mode-btn:hover {
        background-color: var(--color-surface-hover);
        color: var(--color-content-secondary);
    }
    .mode-btn.active {
        color: var(--color-accent);
    }

    .error-popover {
        position: absolute;
        top: 100%;
        right: 0;
        margin-top: 0.5rem;
        width: 16rem;
        background: var(--color-surface-page);
        border: 1px solid var(--color-border);
        border-radius: 10px;
        box-shadow: var(--shadow-float);
        z-index: 50;
        animation: slideUp 0.15s ease-out;
    }

    .popover-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.75rem 0.875rem;
        border-bottom: 1px solid var(--color-border);
    }

    .popover-title {
        font-size: 0.8125rem;
        font-weight: 600;
        color: var(--color-content-primary);
    }

    .popover-close {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 1.5rem;
        height: 1.5rem;
        border-radius: 4px;
        color: var(--color-content-tertiary);
        transition: all 0.15s ease;
    }

    .popover-close:hover {
        color: var(--color-content-primary);
        background: var(--color-surface-hover);
    }

    .popover-desc {
        padding: 0.75rem 0.875rem;
        font-size: 0.75rem;
        line-height: 1.5;
        color: var(--color-content-secondary);
        word-break: break-word;
    }

    /* Modal */
    .modal-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.25);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 1rem;
        z-index: 100;
        animation: fadeIn 0.15s ease-out;
    }

    .modal-container {
        position: relative;
        width: 100%;
        max-width: 360px;
        max-height: calc(100vh - 4rem);
        background: var(--color-surface-page);
        border-radius: 12px;
        border: 1px solid var(--color-border);
        box-shadow: var(--shadow-float);
        overflow: hidden;
        animation: slideUp 0.2s ease-out;
    }

    .modal-header {
        display: flex;
        justify-content: flex-end;
        padding: 0.75rem 0.75rem 0;
    }

    .modal-content {
        padding: 0 1.25rem 1.25rem;
    }

    .close-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 2rem;
        height: 2rem;
        border-radius: 6px;
        color: var(--color-content-tertiary);
        background: var(--color-surface-primary);
        border: 1px solid var(--color-border);
        transition: all 0.15s ease;
    }

    .close-btn:hover {
        color: var(--color-content-primary);
        background: var(--color-surface-hover);
    }

    .conflict-options {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .conflict-option {
        width: 100%;
        padding: 0.875rem 1rem;
        text-align: left;
        background: var(--color-surface-primary);
        border: 1px solid transparent;
        border-radius: 8px;
        transition: all 0.15s ease;
    }

    .conflict-option:hover {
        background: var(--color-surface-hover);
        border-color: var(--color-border);
    }

    .conflict-option:first-child:hover {
        background: var(--color-accent-soft);
        border-color: transparent;
    }

    .conflict-option-alt {
        background: transparent;
    }

    .option-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.125rem;
    }

    .option-label {
        font-size: 0.8125rem;
        font-weight: 500;
        color: var(--color-content-secondary);
    }

    .conflict-option:first-child:hover .option-label {
        color: var(--color-accent);
    }

    .option-badge {
        font-size: 0.625rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: var(--color-srs-good);
        background: rgba(129, 199, 132, 0.15);
        padding: 0.125rem 0.375rem;
        border-radius: 4px;
    }

    .option-time {
        font-size: 0.9375rem;
        font-weight: 600;
        color: var(--color-content-primary);
    }

    .option-desc {
        font-size: 0.75rem;
        color: var(--color-content-tertiary);
        margin-top: 0.125rem;
    }

    @keyframes fadeIn {
        from {
            opacity: 0;
        }
        to {
            opacity: 1;
        }
    }

    @keyframes slideUp {
        from {
            opacity: 0;
            transform: translateY(16px) scale(0.98);
        }
        to {
            opacity: 1;
            transform: translateY(0) scale(1);
        }
    }
</style>
