<script lang="ts">
    import { onMount } from "svelte";
    import type { Snippet } from "svelte";

    interface Props {
        children: Snippet;
    }

    let { children }: Props = $props();

    let container: HTMLDivElement;

    onMount(() => {
        document.body.appendChild(container);
        return () => {
            container?.remove();
        };
    });
</script>

<div bind:this={container} class="portal">
    {@render children()}
</div>

<style>
    .portal {
        display: contents;
    }
</style>
