<script lang="ts">
    import {
        getPWAStore,
        installPWA,
        showIOSInstallGuide,
        hideIOSInstallGuide,
        dismissInstallBanner,
    } from "$lib/stores/pwa.svelte";

    const pwa = getPWAStore();

    async function handleInstall() {
        if (pwa.isIOS) {
            showIOSInstallGuide();
        } else {
            await installPWA();
        }
    }
</script>

{#if pwa.showInstallBanner && !pwa.isStandalone}
    <div class="install-banner">
        <div class="banner-content">
            <div class="banner-icon">
                <svg
                    viewBox="0 0 32 32"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                >
                    <rect
                        x="4"
                        y="6"
                        width="18"
                        height="14"
                        rx="2"
                        fill="currentColor"
                        opacity="0.25"
                    />
                    <rect
                        x="7"
                        y="9"
                        width="18"
                        height="14"
                        rx="2"
                        fill="currentColor"
                        opacity="0.5"
                    />
                    <rect
                        x="10"
                        y="12"
                        width="18"
                        height="14"
                        rx="2"
                        fill="currentColor"
                    />
                </svg>
            </div>
            <div class="banner-text">
                <h3>安裝到桌面</h3>
                <p>免下載，離線也能背單字</p>
            </div>
        </div>
        <div class="banner-actions">
            <button class="install-btn" onclick={handleInstall}>
                {pwa.isIOS ? "查看步驟" : "安裝"}
            </button>
            <button
                class="dismiss-btn"
                onclick={dismissInstallBanner}
                aria-label="關閉"
            >
                <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                >
                    <path
                        d="M6 18L18 6M6 6l12 12"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                    />
                </svg>
            </button>
        </div>
    </div>
{/if}

{#if pwa.showIOSGuide}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        class="ios-guide-overlay"
        onclick={hideIOSInstallGuide}
        onkeydown={(e) => e.key === "Escape" && hideIOSInstallGuide()}
        role="presentation"
    >
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
            class="ios-guide-content"
            onclick={(e) => e.stopPropagation()}
            onkeydown={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="ios-guide-title"
            tabindex="-1"
        >
            <h4 id="ios-guide-title">如何加入主畫面</h4>
            <ol class="guide-steps">
                <li>
                    <span class="step-number">1</span>
                    <div class="step-content">
                        <span>點擊 Safari 下方的分享按鈕</span>
                        <div class="share-icon">
                            <svg viewBox="0 0 24 24" fill="currentColor">
                                <path
                                    d="M16 5l-1.42 1.42-1.59-1.59V16h-1.98V4.83L9.42 6.42 8 5l4-4 4 4zm4 5v11c0 1.1-.9 2-2 2H6c-1.11 0-2-.9-2-2V10c0-1.11.89-2 2-2h3v2H6v11h12V10h-3V8h3c1.1 0 2 .89 2 2z"
                                />
                            </svg>
                        </div>
                    </div>
                </li>
                <li>
                    <span class="step-number">2</span>
                    <span>捲動並選擇「加入主畫面」選項</span>
                </li>
                <li>
                    <span class="step-number">3</span>
                    <span>點擊「加入」完成安裝</span>
                </li>
                <li>
                    <span class="step-number">4</span>
                    <span>在主畫面開啟享受最佳體驗</span>
                </li>
            </ol>
            <button class="close-guide-btn" onclick={hideIOSInstallGuide}
                >我知道了</button
            >
        </div>
        <div class="arrow-indicator">
            <svg viewBox="0 0 24 24" fill="currentColor">
                <path
                    d="M20 12l-1.41-1.41L13 16.17V4h-2v12.17l-5.58-5.59L4 12l8 8 8-8z"
                />
            </svg>
        </div>
    </div>
{/if}

<style>
    .install-banner {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        z-index: 1000;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        padding: 12px 16px;
        background: var(--color-surface-primary);
        border-top: 1px solid var(--color-border);
        box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.1);
    }

    .banner-content {
        display: flex;
        align-items: center;
        gap: 12px;
        flex: 1;
        min-width: 0;
    }

    .banner-icon {
        width: 40px;
        height: 40px;
        flex-shrink: 0;
        color: var(--color-accent);
    }

    .banner-icon svg {
        width: 100%;
        height: 100%;
    }

    .banner-text {
        min-width: 0;
    }

    .banner-text h3 {
        font-size: 15px;
        font-weight: 600;
        color: var(--color-content-primary);
        margin: 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .banner-text p {
        font-size: 13px;
        color: var(--color-content-secondary);
        margin: 2px 0 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .banner-actions {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-shrink: 0;
    }

    .install-btn {
        padding: 8px 16px;
        background: var(--color-accent);
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        transition: background 0.2s;
    }

    .install-btn:hover {
        background: var(--color-accent-hover);
    }

    .dismiss-btn {
        width: 32px;
        height: 32px;
        padding: 4px;
        background: none;
        border: none;
        color: var(--color-content-tertiary);
        cursor: pointer;
        border-radius: 6px;
        transition: background 0.2s;
    }

    .dismiss-btn:hover {
        background: var(--color-surface-secondary);
    }

    .dismiss-btn svg {
        width: 100%;
        height: 100%;
    }

    .ios-guide-overlay {
        position: fixed;
        inset: 0;
        z-index: 10000;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(0, 0, 0, 0.7);
        animation: fadeIn 0.3s ease;
    }

    @keyframes fadeIn {
        from {
            opacity: 0;
        }
        to {
            opacity: 1;
        }
    }

    .ios-guide-content {
        position: relative;
        width: calc(100% - 32px);
        max-width: 360px;
        margin-bottom: 80px;
        padding: 24px;
        background: var(--color-surface-primary);
        border-radius: 16px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }

    .ios-guide-content h4 {
        font-size: 20px;
        font-weight: 700;
        color: var(--color-content-primary);
        margin: 0 0 20px;
    }

    .guide-steps {
        list-style: none;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 16px;
    }

    .guide-steps li {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .step-number {
        width: 28px;
        height: 28px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--color-accent);
        color: white;
        border-radius: 50%;
        font-size: 14px;
        font-weight: 700;
        flex-shrink: 0;
    }

    .step-content {
        display: flex;
        align-items: center;
        gap: 8px;
        flex: 1;
    }

    .share-icon {
        width: 36px;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--color-surface-secondary);
        border-radius: 8px;
        flex-shrink: 0;
    }

    .share-icon svg {
        width: 20px;
        height: 20px;
        color: var(--color-accent);
    }

    .guide-steps span:not(.step-number) {
        font-size: 15px;
        color: var(--color-content-secondary);
    }

    .close-guide-btn {
        width: 100%;
        margin-top: 24px;
        padding: 14px;
        background: var(--color-accent);
        color: white;
        border: none;
        border-radius: 12px;
        font-size: 16px;
        font-weight: 500;
        cursor: pointer;
        transition: background 0.2s;
    }

    .close-guide-btn:hover {
        background: var(--color-accent-hover);
    }

    .arrow-indicator {
        position: absolute;
        bottom: 40px;
        left: 50%;
        transform: translateX(-50%);
        animation: bounce 1s infinite;
    }

    .arrow-indicator svg {
        width: 48px;
        height: 48px;
        color: white;
        filter: drop-shadow(0 2px 8px rgba(0, 0, 0, 0.3));
    }

    @keyframes bounce {
        0%,
        100% {
            transform: translateX(-50%) translateY(0);
        }
        50% {
            transform: translateX(-50%) translateY(10px);
        }
    }
</style>
