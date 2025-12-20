<script lang="ts">
    import type { LoadProgress } from "$lib/stores/vocab-loader";

    interface Props {
        progress: LoadProgress;
    }

    const { progress }: Props = $props();

    const percentage = $derived(
        progress.total > 0
            ? Math.round((progress.current / progress.total) * 100)
            : 0,
    );

    const isIndeterminate = $derived(
        progress.phase === "checking" ||
            progress.phase === "downloading" ||
            progress.phase === "decompressing",
    );
</script>

<div
    class="fixed inset-0 bg-surface-page flex flex-col items-center justify-center z-50"
>
    <div class="flex flex-col items-center gap-6 max-w-md w-full px-8">
        <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 32 32"
            class="w-16 h-16"
        >
            <rect
                x="4"
                y="6"
                width="18"
                height="14"
                rx="2"
                fill="currentColor"
                class="text-accent/25"
            />
            <rect
                x="7"
                y="9"
                width="18"
                height="14"
                rx="2"
                fill="currentColor"
                class="text-accent/50"
            />
            <rect
                x="10"
                y="12"
                width="18"
                height="14"
                rx="2"
                fill="currentColor"
                class="text-accent"
            />
        </svg>

        <h1
            class="text-xl font-semibold tracking-tight text-content-primary text-center"
        >
            {progress.message}
        </h1>

        <div class="w-full">
            <div
                class="w-full h-2 bg-surface-secondary rounded-full overflow-hidden"
            >
                {#if isIndeterminate}
                    <div
                        class="h-full w-[30%] bg-accent rounded-full animate-indeterminate"
                    ></div>
                {:else}
                    <div
                        class="h-full bg-accent rounded-full transition-all duration-300 ease-out"
                        style="width: {percentage}%"
                    ></div>
                {/if}
            </div>

            <style>
                @keyframes indeterminate {
                    0% {
                        transform: translateX(-100%);
                    }
                    100% {
                        transform: translateX(433%);
                    }
                }

                .animate-indeterminate {
                    animation: indeterminate 1.5s ease-in-out infinite;
                }
            </style>

            {#if progress.phase === "storing" && progress.total > 0}
                <p class="text-sm text-content-secondary text-center mt-3">
                    {percentage}% ({progress.current.toLocaleString()} / {progress.total.toLocaleString()})
                </p>
            {/if}
        </div>

        <p class="text-xs text-content-tertiary text-center">
            首次載入需要約 10-15 秒，之後將即時啟動
        </p>
    </div>
</div>
