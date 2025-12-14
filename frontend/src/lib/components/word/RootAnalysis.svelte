<script lang="ts">
    import type { RootInfo } from "$lib/types/vocab";

    interface Props {
        rootInfo: RootInfo;
    }

    let { rootInfo }: Props = $props();
</script>

<div class="root-analysis space-y-3">
    {#if rootInfo.root_breakdown}
        <div class="breakdown">
            <h4 class="text-xs font-medium text-content-tertiary mb-1">
                字根拆解
            </h4>
            <p class="text-sm text-content-primary font-mono bg-surface-page px-3 py-2 rounded-md">
                {rootInfo.root_breakdown}
            </p>
        </div>
    {/if}

    <div class="strategy">
        <h4 class="text-xs font-medium text-content-tertiary mb-1">
            記憶策略
        </h4>
        <p class="text-sm text-content-secondary leading-relaxed">
            {rootInfo.memory_strategy}
        </p>
    </div>
</div>
