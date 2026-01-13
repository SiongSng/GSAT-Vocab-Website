<script lang="ts">
    interface Props {
        message?: string;
    }

    let { message = "正在同步學習進度..." }: Props = $props();
</script>

<div class="sync-container">
    <div class="spinner"></div>
    <p>{message}</p>
</div>

<style>
    .sync-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1rem;
        padding: 3rem 0;
        color: var(--color-content-secondary);
    }

    .spinner {
        width: 28px;
        height: 28px;
        border: 2.5px solid var(--color-surface-secondary);
        border-top-color: var(--color-content-primary);
        border-radius: 50%;
        animation: spin 0.7s linear infinite;
    }

    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }

    p {
        font-size: 0.9375rem;
        margin: 0;
    }
</style>
