<script lang="ts">
    import { onMount } from "svelte";
    import {
        getNotificationStore,
        initNotifications,
        toggleNotifications,
        updateNotificationSettings,
        testNotification,
    } from "$lib/stores/notifications.svelte";
    import { getAppStore } from "$lib/stores/app.svelte";

    interface Props {
        showTitle?: boolean;
    }

    let { showTitle = true }: Props = $props();

    const notifications = getNotificationStore();
    const app = getAppStore();

    let isToggling = $state(false);

    // Derived values for time selectors
    let selectedHour = $derived(
        notifications.settings.dailyReminderTime.split(":")[0],
    );
    let selectedMinute = $derived(
        notifications.settings.dailyReminderTime.split(":")[1],
    );

    const HOURS = Array.from({ length: 24 }, (_, i) =>
        String(i).padStart(2, "0"),
    );
    const MINUTES = Array.from({ length: 60 }, (_, i) =>
        String(i).padStart(2, "0"),
    );

    onMount(() => {
        initNotifications();
    });

    async function handleToggle() {
        if (isToggling) return;
        isToggling = true;

        const newEnabled = !notifications.settings.enabled;
        await toggleNotifications(newEnabled);

        isToggling = false;
    }

    function updateTime(hour: string, minute: string) {
        updateNotificationSettings({ dailyReminderTime: `${hour}:${minute}` });
    }

    function handleHourChange(event: Event) {
        const target = event.target as HTMLSelectElement;
        updateTime(target.value, selectedMinute);
    }

    function handleMinuteChange(event: Event) {
        const target = event.target as HTMLSelectElement;
        updateTime(selectedHour, target.value);
    }

    function handleStreakWarningToggle() {
        updateNotificationSettings({
            streakWarningEnabled: !notifications.settings.streakWarningEnabled,
        });
    }

    function handleDueReminderToggle() {
        updateNotificationSettings({
            dueCardReminderEnabled:
                !notifications.settings.dueCardReminderEnabled,
        });
    }

    function handleTest() {
        testNotification();
    }
</script>

<div class="notification-settings">
    {#if showTitle && !app.isMobile}
        <h4 class="setting-group-title">學習提醒</h4>
    {/if}

    {#if !notifications.isSupported}
        <div class="notice notice-muted">
            <svg class="notice-icon" viewBox="0 0 20 20" fill="currentColor">
                <path
                    fill-rule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z"
                    clip-rule="evenodd"
                />
            </svg>
            <span>你的瀏覽器不支援通知功能</span>
        </div>
    {:else if notifications.permission === "denied"}
        <div class="notice notice-error">
            <svg class="notice-icon" viewBox="0 0 20 20" fill="currentColor">
                <path
                    fill-rule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z"
                    clip-rule="evenodd"
                />
            </svg>
            <span>通知權限已被封鎖，請到瀏覽器設定中允許</span>
        </div>
    {:else}
        <div class="settings-list">
            <div class="setting-row">
                <span class="setting-label">啟用每日提醒</span>
                <button
                    type="button"
                    onclick={handleToggle}
                    class="toggle"
                    class:toggle-active={notifications.settings.enabled}
                    role="switch"
                    aria-checked={notifications.settings.enabled}
                    aria-label="啟用通知"
                    disabled={isToggling}
                >
                    <span class="toggle-thumb"></span>
                </button>
            </div>

            {#if notifications.settings.enabled}
                <div class="setting-row time-row">
                    <span class="setting-label">提醒時間</span>
                    <div class="custom-time-picker">
                        <div class="select-wrapper">
                            <select
                                value={selectedHour}
                                onchange={handleHourChange}
                                class="time-select"
                            >
                                {#each HOURS as h}
                                    <option value={h}>{h}</option>
                                {/each}
                            </select>
                            <svg
                                class="select-arrow"
                                viewBox="0 0 20 20"
                                fill="currentColor"
                            >
                                <path
                                    fill-rule="evenodd"
                                    d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
                                    clip-rule="evenodd"
                                />
                            </svg>
                        </div>
                        <span class="time-divider">:</span>
                        <div class="select-wrapper">
                            <select
                                value={selectedMinute}
                                onchange={handleMinuteChange}
                                class="time-select"
                            >
                                {#each MINUTES as m}
                                    <option value={m}>{m}</option>
                                {/each}
                            </select>
                            <svg
                                class="select-arrow"
                                viewBox="0 0 20 20"
                                fill="currentColor"
                            >
                                <path
                                    fill-rule="evenodd"
                                    d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
                                    clip-rule="evenodd"
                                />
                            </svg>
                        </div>
                    </div>
                </div>

                <div class="setting-sub-group">
                    <p class="sub-group-hint">
                        以下提醒需要 App 在前景執行才會生效
                    </p>
                    <div class="setting-row">
                        <span class="setting-label sub-label"
                            >連續學習天數提醒</span
                        >
                        <button
                            type="button"
                            onclick={handleStreakWarningToggle}
                            class="toggle toggle-sm"
                            class:toggle-active={notifications.settings
                                .streakWarningEnabled}
                            role="switch"
                            aria-checked={notifications.settings
                                .streakWarningEnabled}
                            aria-label="連續學習天數提醒"
                        >
                            <span class="toggle-thumb"></span>
                        </button>
                    </div>

                    <div class="setting-row">
                        <span class="setting-label sub-label">到期卡片提醒</span
                        >
                        <button
                            type="button"
                            onclick={handleDueReminderToggle}
                            class="toggle toggle-sm"
                            class:toggle-active={notifications.settings
                                .dueCardReminderEnabled}
                            role="switch"
                            aria-checked={notifications.settings
                                .dueCardReminderEnabled}
                            aria-label="到期卡片提醒"
                        >
                            <span class="toggle-thumb"></span>
                        </button>
                    </div>
                </div>

                <div class="test-row">
                    <button type="button" class="test-btn" onclick={handleTest}>
                        測試通知
                    </button>
                </div>
            {/if}
        </div>
    {/if}
</div>

<style>
    .notification-settings {
        display: flex;
        flex-direction: column;
    }

    .setting-group-title {
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--color-section-header);
        margin: 0 0 1rem 0;
    }

    /* Notice Styles */
    .notice {
        display: flex;
        align-items: flex-start;
        gap: 0.5rem;
        padding: 0.75rem;
        border-radius: 0.5rem;
        font-size: 0.8125rem;
        line-height: 1.4;
    }

    .notice-muted {
        background-color: var(--color-surface-secondary);
        color: var(--color-content-secondary);
    }

    .notice-error {
        background-color: var(--color-srs-again-soft);
        color: var(--color-srs-again);
    }

    .notice-icon {
        width: 1rem;
        height: 1rem;
        flex-shrink: 0;
        margin-top: 0.125rem;
    }

    /* Settings List */
    .settings-list {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }

    .setting-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        padding: 0.625rem 0;
    }

    .time-row {
        padding-top: 1rem;
    }

    .setting-label {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--color-content-primary);
    }

    .sub-label {
        font-size: 0.8125rem;
        color: var(--color-content-secondary);
    }

    .setting-sub-group {
        margin-top: 0.5rem;
        padding-top: 0.5rem;
        border-top: 1px dashed var(--color-border);
    }

    .sub-group-hint {
        font-size: 0.75rem;
        color: var(--color-content-tertiary);
        margin: 0 0 0.5rem 0;
    }

    /* Toggle Switch */
    .toggle {
        position: relative;
        width: 2rem;
        height: 1.125rem;
        background-color: var(--color-border-hover);
        border-radius: 0.5625rem;
        cursor: pointer;
        transition: background-color 0.15s ease;
        flex-shrink: 0;
        border: none;
        padding: 0;
    }

    .toggle:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .toggle-active {
        background-color: var(--color-content-primary);
    }

    .toggle-thumb {
        position: absolute;
        top: 0.1875rem;
        left: 0.1875rem;
        width: 0.75rem;
        height: 0.75rem;
        background-color: white;
        border-radius: 50%;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
        transition: transform 0.15s ease;
    }

    .toggle-active .toggle-thumb {
        transform: translateX(0.875rem);
    }

    /* Custom Time Picker */
    .custom-time-picker {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .select-wrapper {
        position: relative;
        display: flex;
        align-items: center;
    }

    .time-select {
        appearance: none;
        -webkit-appearance: none;
        background-color: var(--color-surface-secondary);
        border: 1px solid transparent;
        border-radius: 0.5rem;
        padding: 0.375rem 2rem 0.375rem 0.75rem;
        font-size: 0.875rem;
        font-family: inherit;
        font-weight: 500;
        color: var(--color-content-primary);
        cursor: pointer;
        transition: all 0.15s ease;
    }

    .time-select:hover {
        background-color: var(--color-surface-hover);
        border-color: var(--color-border-hover);
    }

    .time-select:focus {
        outline: none;
        background-color: var(--color-surface-page);
        border-color: var(--color-accent);
        box-shadow: 0 0 0 3px var(--color-accent-soft);
    }

    .select-arrow {
        position: absolute;
        right: 0.5rem;
        width: 1rem;
        height: 1rem;
        color: var(--color-content-tertiary);
        pointer-events: none;
    }

    .time-divider {
        font-weight: 600;
        color: var(--color-content-tertiary);
    }

    /* Test Button */
    .test-row {
        margin-top: 1rem;
        padding-top: 0.75rem;
        border-top: 1px solid var(--color-border);
    }

    .test-btn {
        width: 100%;
        padding: 0.625rem 1rem;
        background-color: transparent;
        border: 1px solid var(--color-border);
        border-radius: 0.5rem;
        font-size: 0.8125rem;
        font-weight: 500;
        color: var(--color-content-secondary);
        cursor: pointer;
        transition: all 0.15s ease;
    }

    .test-btn:hover {
        background-color: var(--color-surface-hover);
        border-color: var(--color-content-tertiary);
        color: var(--color-content-primary);
    }
</style>
