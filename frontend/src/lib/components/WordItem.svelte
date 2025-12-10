<script lang="ts">
  import type { VocabIndexItem } from '$lib/api';

  interface Props {
    word: VocabIndexItem;
    rank: number;
    isGridMode?: boolean;
    isActive?: boolean;
    onclick?: () => void;
  }

  let {
    word,
    rank,
    isGridMode = false,
    isActive = false,
    onclick
  }: Props = $props();
</script>

{#if isGridMode}
  <button
    class="browse-cell {isActive ? 'active-item' : ''}"
    onclick={onclick}
    type="button"
  >
    {word.lemma}
  </button>
{:else}
  <button
    class="list-item flex justify-between items-center p-3 px-4 cursor-pointer border-b border-slate-100 hover:bg-slate-100 transition-colors duration-150 w-full text-left {isActive ? 'active-item' : ''}"
    onclick={onclick}
    type="button"
  >
    <div class="flex-1 min-w-0">
      <div class="flex items-center gap-2 flex-wrap">
        <span class="font-semibold text-slate-800">{word.lemma}</span>
        <span class="text-xs font-medium text-slate-500">{word.primary_pos}</span>
        {#if word.meaning_count > 1}
          <span class="text-xs px-1.5 py-0.5 bg-indigo-100 text-indigo-700 rounded">
            {word.meaning_count}義
          </span>
        {/if}
      </div>
      {#if word.zh_preview}
        <p class="text-xs text-slate-600 mt-1 truncate">
          {word.zh_preview.slice(0, 40)}...
        </p>
      {/if}
    </div>
    <div class="flex items-center gap-3 flex-shrink-0">
      <span class="text-xs text-slate-400">#{rank}</span>
      <span class="text-sm font-mono bg-slate-200 text-slate-600 px-2 py-0.5 rounded-full">
        {word.count}
      </span>
    </div>
  </button>
{/if}

<style>
  .browse-cell {
    padding: 0.5rem 0.75rem;
    background-color: white;
    border-radius: 0.5rem;
    font-size: 0.875rem;
    font-weight: 500;
    color: rgb(51 65 85);
    border: 1px solid rgb(226 232 240);
    cursor: pointer;
    transition: all 0.15s ease;
    text-align: center;
  }

  .browse-cell:hover {
    background-color: rgb(241 245 249);
    border-color: rgb(199 210 254);
    transform: translateY(-1px);
  }

  .browse-cell.active-item {
    background-color: rgb(238 242 255);
    border-color: rgb(129 140 248);
    color: rgb(67 56 202);
  }

  .list-item.active-item {
    background-color: rgb(238 242 255);
  }
</style>
