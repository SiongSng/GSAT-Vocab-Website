<script lang="ts">
    import {
        getTTSSettingsStore,
        setEngine,
        type TTSEngine,
    } from "$lib/stores/tts-settings.svelte";
    import { loadKokoroModel, unloadKokoro } from "$lib/kokoro-tts";
    import { clearAudioCache } from "$lib/tts";

    const ttsSettings = getTTSSettingsStore();

    let isDownloading = $state(false);

    async function handleEngineChange(engine: TTSEngine) {
        if (engine === ttsSettings.engine) return;

        if (engine === "kokoro") {
            if (ttsSettings.kokoro.status !== "ready") {
                isDownloading = true;
                try {
                    await loadKokoroModel();
                    setEngine("kokoro");
                    clearAudioCache();
                } catch {
                    // error is handled in kokoro-tts
                } finally {
                    isDownloading = false;
                }
            } else {
                setEngine("kokoro");
                clearAudioCache();
            }
        } else {
            setEngine("edge-tts");
            clearAudioCache();
        }
    }

    let isDeleting = $state(false);

    async function handleDeleteModel() {
        isDeleting = true;
        try {
            await unloadKokoro();
            if (ttsSettings.engine === "kokoro") {
                setEngine("edge-tts");
                clearAudioCache();
            }
        } finally {
            isDeleting = false;
        }
    }

    const isKokoroReady = $derived(ttsSettings.kokoro.status === "ready");
    const isKokoroError = $derived(ttsSettings.kokoro.status === "error");
</script>

<div class="tts-settings">
    <h3 class="section-header">語音引擎</h3>

    <div class="engine-options">
        <button
            type="button"
            class="engine-option"
            class:active={ttsSettings.engine === "edge-tts"}
            onclick={() => handleEngineChange("edge-tts")}
            disabled={isDownloading}
        >
            <div class="option-content">
                <span class="option-label">雲端語音</span>
                <span class="option-desc">免下載，但連線經常不穩定</span>
            </div>
            {#if ttsSettings.engine === "edge-tts"}
                <svg class="check-icon" viewBox="0 0 20 20" fill="currentColor">
                    <path
                        fill-rule="evenodd"
                        d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
                        clip-rule="evenodd"
                    />
                </svg>
            {/if}
        </button>

        <button
            type="button"
            class="engine-option"
            class:active={ttsSettings.engine === "kokoro"}
            onclick={() => handleEngineChange("kokoro")}
            disabled={isDownloading}
        >
            <div class="option-content">
                <span class="option-label">
                    離線模型
                    {#if isKokoroReady}
                        <span class="badge badge-ready">已下載</span>
                    {:else if !isDownloading}
                        <span class="badge badge-size">~87MB</span>
                    {/if}
                </span>
                <span class="option-desc"
                    >更自然，需較高效能裝置（如 M 系列 Mac）</span
                >
            </div>
            {#if ttsSettings.engine === "kokoro"}
                <svg class="check-icon" viewBox="0 0 20 20" fill="currentColor">
                    <path
                        fill-rule="evenodd"
                        d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
                        clip-rule="evenodd"
                    />
                </svg>
            {/if}
        </button>
    </div>

    {#if isDownloading}
        <div class="download-progress">
            <div class="progress-bar">
                <div
                    class="progress-fill"
                    style="width: {ttsSettings.kokoro.downloadProgress}%"
                ></div>
            </div>
            <span class="progress-text"
                >下載中... {ttsSettings.kokoro.downloadProgress}%</span
            >
        </div>
    {/if}

    {#if isKokoroError}
        <div class="notice notice-error">
            <span>下載失敗：{ttsSettings.kokoro.error}</span>
        </div>
    {/if}

    {#if isKokoroReady && ttsSettings.engine !== "kokoro"}
        <button
            type="button"
            class="delete-btn"
            onclick={handleDeleteModel}
            disabled={isDeleting}
        >
            {isDeleting ? "刪除中..." : "刪除離線模型"}
        </button>
    {/if}
</div>

<style>
    .tts-settings {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .section-header {
        font-size: 0.8125rem;
        font-weight: 600;
        color: var(--color-section-header);
        line-height: 1;
        margin: 0;
    }

    .engine-options {
        display: flex;
        flex-direction: column;
        gap: 0.375rem;
    }

    .engine-option {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.75rem;
        padding: 0.625rem 0.75rem;
        background-color: var(--color-surface-page);
        border: 1px solid transparent;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.15s ease;
        text-align: left;
        width: 100%;
    }

    .engine-option:hover:not(:disabled) {
        background-color: var(--color-surface-hover);
        border-color: var(--color-border);
    }

    .engine-option:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }

    .engine-option.active {
        background-color: var(--color-accent-soft);
        border-color: transparent;
    }

    .option-content {
        display: flex;
        flex-direction: column;
        gap: 0.125rem;
    }

    .option-label {
        font-size: 0.8125rem;
        font-weight: 500;
        color: var(--color-content-primary);
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .option-desc {
        font-size: 0.6875rem;
        color: var(--color-content-tertiary);
    }

    .badge {
        font-size: 0.5625rem;
        font-weight: 500;
        padding: 0.0625rem 0.3125rem;
        border-radius: 9999px;
    }

    .badge-size {
        background-color: var(--color-surface-hover);
        color: var(--color-content-secondary);
    }

    .badge-ready {
        background-color: var(--color-srs-good);
        color: white;
    }

    .check-icon {
        width: 1rem;
        height: 1rem;
        color: var(--color-accent);
        flex-shrink: 0;
    }

    .download-progress {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
        margin-top: 0.25rem;
    }

    .progress-bar {
        height: 3px;
        background-color: var(--color-surface-secondary);
        border-radius: 2px;
        overflow: hidden;
    }

    .progress-fill {
        height: 100%;
        background-color: var(--color-accent);
        transition: width 0.2s ease;
    }

    .progress-text {
        font-size: 0.6875rem;
        color: var(--color-content-secondary);
    }

    .notice {
        padding: 0.5rem 0.625rem;
        border-radius: 6px;
        font-size: 0.75rem;
        margin-top: 0.25rem;
    }

    .notice-error {
        background-color: var(--color-srs-again-soft);
        color: var(--color-srs-again);
    }

    .delete-btn {
        padding: 0.375rem 0.625rem;
        background-color: transparent;
        border: 1px solid var(--color-border);
        border-radius: 6px;
        font-size: 0.75rem;
        color: var(--color-content-secondary);
        cursor: pointer;
        transition: all 0.15s ease;
        margin-top: 0.25rem;
    }

    .delete-btn:hover {
        background-color: var(--color-srs-again-soft);
        border-color: var(--color-srs-again);
        color: var(--color-srs-again);
    }
</style>
