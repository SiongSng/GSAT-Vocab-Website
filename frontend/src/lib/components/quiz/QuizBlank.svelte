<script lang="ts">
    interface Props {
        length?: number;
        active?: boolean;
    }

    let { length = 6, active = false }: Props = $props();

    const width = $derived(`${Math.max(4, length)}ch`);
</script>

<span
    class="quiz-blank"
    class:active
    style:width={width}
    aria-hidden="true"
></span>

<style>
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
