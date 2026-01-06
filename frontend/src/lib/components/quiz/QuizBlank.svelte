<script lang="ts">
    interface Props {
        length?: number;
        active?: boolean;
        prefix?: string;
        suffix?: string;
    }

    let { length = 6, active = false, prefix = "", suffix = "" }: Props = $props();

    const hasHints = $derived(prefix || suffix);
    const width = $derived(
        hasHints ? `${Math.max(2, length)}ch` : `${Math.max(4, length)}ch`
    );
</script>

{#if hasHints}
    <span class="quiz-blank-with-hints" class:active>
        {#if prefix}
            <span class="hint-text prefix">{prefix}</span>
        {/if}
        <span class="quiz-blank blank-part" class:active style:width={width}></span>
        {#if suffix}
            <span class="hint-text suffix">{suffix}</span>
        {/if}
    </span>
{:else}
    <span
        class="quiz-blank"
        class:active
        style:width={width}
        aria-hidden="true"
    ></span>
{/if}

<style>
    .quiz-blank-with-hints {
        display: inline-flex;
        align-items: baseline;
        vertical-align: baseline;
        margin: 0 0.15em;
    }

    .hint-text {
        font-weight: 600;
        color: var(--color-content-primary);
        letter-spacing: 0.02em;
    }

    .hint-text.prefix {
        margin-right: 0.05em;
    }

    .hint-text.suffix {
        margin-left: 0.05em;
    }

    .blank-part {
        display: inline-block;
        vertical-align: baseline;
        height: 1.1em;
        border-bottom: 2px solid var(--color-border);
        transition: all 0.2s ease-out;
    }

    .blank-part.active {
        border-bottom-color: var(--color-accent);
        border-bottom-width: 2.5px;
        animation: glow 1.8s ease-in-out infinite;
    }

    .quiz-blank {
        display: inline-block;
        vertical-align: baseline;
        height: 1.1em;
        margin: 0 0.15em;
        border-bottom: 2px solid var(--color-border);
        transition: all 0.2s ease-out;
    }

    .quiz-blank.active {
        border-bottom-color: var(--color-accent);
        border-bottom-width: 2.5px;
        animation: glow 1.8s ease-in-out infinite;
    }

    @keyframes glow {
        0%, 100% {
            box-shadow: 0 2px 4px rgba(var(--color-accent-rgb), 0.3);
        }
        50% {
            box-shadow: 0 2px 12px rgba(var(--color-accent-rgb), 0.6);
        }
    }
</style>
