<script lang="ts">
    import {
        createAudioController,
        isAudioCached,
        subscribeToGlobalAudioState,
        type AudioState,
    } from "$lib/tts";

    interface Props {
        text: string;
        size?: "sm" | "md" | "lg";
        variant?: "ghost" | "subtle";
        class?: string;
    }

    let {
        text,
        size = "md",
        variant = "ghost",
        class: className = "",
    }: Props = $props();

    let localState = $state<AudioState>("idle");
    let globalState = $state<AudioState>("idle");
    let globalText = $state<string | null>(null);
    let controller = $state<ReturnType<typeof createAudioController> | null>(
        null,
    );

    const isCached = $derived(isAudioCached(text));
    const isGlobalMatch = $derived(globalText === text);
    const audioState = $derived(isGlobalMatch ? globalState : localState);

    $effect(() => {
        const ctrl = createAudioController(() => text);
        controller = ctrl;

        const unsubscribeLocal = ctrl.subscribe((state) => {
            localState = state;
        });

        const unsubscribeGlobal = subscribeToGlobalAudioState(
            (playingText, state) => {
                globalText = playingText;
                globalState = state;
            },
        );

        return () => {
            unsubscribeLocal();
            unsubscribeGlobal();
            ctrl.stop();
        };
    });

    function handleClick() {
        if (!controller) return;

        if (audioState === "playing") {
            controller.stop();
        } else if (audioState !== "loading") {
            controller.play();
        }
    }

    const sizeClasses = {
        sm: "w-7 h-7 p-1",
        md: "w-8 h-8 p-1.5",
        lg: "w-10 h-10 p-2",
    };

    const iconSizes = {
        sm: "w-3.5 h-3.5",
        md: "w-4 h-4",
        lg: "w-5 h-5",
    };

    const variantClasses = {
        ghost: "hover:bg-surface-hover",
        subtle: "bg-surface-secondary hover:bg-surface-hover",
    };
</script>

<button
    type="button"
    class="audio-button {sizeClasses[size]} {variantClasses[
        variant
    ]} {className}"
    class:loading={audioState === "loading"}
    class:playing={audioState === "playing"}
    class:error={audioState === "error"}
    class:cached={isCached}
    onclick={handleClick}
    disabled={audioState === "loading"}
    title={audioState === "loading"
        ? "載入中..."
        : audioState === "playing"
          ? "停止播放"
          : "播放發音"}
>
    {#if audioState === "loading"}
        <svg class="spinner {iconSizes[size]}" viewBox="0 0 24 24" fill="none">
            <circle
                class="spinner-track"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="2.5"
            />
            <path
                class="spinner-head"
                d="M12 2a10 10 0 0 1 10 10"
                stroke="currentColor"
                stroke-width="2.5"
                stroke-linecap="round"
            />
        </svg>
    {:else if audioState === "playing"}
        <svg
            class="{iconSizes[size]} text-accent"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke-width="1.5"
            stroke="currentColor"
        >
            <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M15.75 5.25v13.5m-7.5-13.5v13.5"
            />
        </svg>
    {:else if audioState === "error"}
        <svg
            class="{iconSizes[size]} text-srs-again"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke-width="1.5"
            stroke="currentColor"
        >
            <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z"
            />
        </svg>
    {:else}
        <svg
            class="{iconSizes[size]} icon-speaker"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke-width="1.5"
            stroke="currentColor"
        >
            <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M19.114 5.636a9 9 0 0 1 0 12.728M16.463 8.288a5.25 5.25 0 0 1 0 7.424M6.75 8.25l4.72-4.72a.75.75 0 0 1 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z"
            />
        </svg>
    {/if}
</button>

<style>
    .audio-button {
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 6px;
        transition: all 0.15s ease;
        flex-shrink: 0;
    }

    .audio-button:disabled {
        cursor: not-allowed;
    }

    .audio-button .icon-speaker {
        color: var(--color-content-tertiary);
        transition: color 0.15s ease;
    }

    .audio-button:hover:not(:disabled) .icon-speaker {
        color: var(--color-content-secondary);
    }

    .audio-button.cached .icon-speaker {
        color: var(--color-content-secondary);
    }

    .audio-button.cached:hover:not(:disabled) .icon-speaker {
        color: var(--color-accent);
    }

    .audio-button.playing {
        background-color: var(--color-accent-soft);
    }

    .audio-button.error {
        background-color: var(--color-srs-again-soft);
    }

    .spinner {
        animation: spin 0.8s linear infinite;
    }

    .spinner-track {
        opacity: 0.2;
    }

    .spinner-head {
        color: var(--color-accent);
    }

    @keyframes spin {
        from {
            transform: rotate(0deg);
        }
        to {
            transform: rotate(360deg);
        }
    }
</style>
