<script lang="ts">
  import { getAuthStore } from "$lib/stores/auth.svelte";
  import { getSyncStore } from "$lib/stores/sync.svelte";
  import { fade } from "svelte/transition";

  const auth = getAuthStore();
  const sync = getSyncStore();

  let showConflictDialog = $state(false);
  let showErrorPopover = $state(false);
  let conflictData = $state<{ cloudTime: number; localTime: number } | null>(null);

  const STALE_THRESHOLD = 24 * 60 * 60 * 1000; // 24 hours
  const isStale = $derived(auth.user && (Date.now() - sync.lastSyncTime > STALE_THRESHOLD));

  async function handleSync() {
    if (sync.status === 'syncing') return;
    
    // If already in error state, clicking shows the popover
    if (sync.status === 'error' && !showErrorPopover) {
      showErrorPopover = true;
      return;
    }

    showErrorPopover = false;
    if (!auth.user) {
      try {
        await auth.login();
      } catch (e) {
        return;
      }
    }

    try {
      const result = await sync.syncWithCloud();
      if (result?.conflict) {
        conflictData = { cloudTime: result.cloudTime, localTime: result.localTime };
        showConflictDialog = true;
      } else if (result?.rateLimited || sync.status === 'error') {
        showErrorPopover = true;
      }
    } catch (e) {
      console.error("Sync error:", e);
      showErrorPopover = true;
    }
  }

  async function resolveConflict(overwriteLocal: boolean) {
    showConflictDialog = false;
    if (overwriteLocal) {
      await sync.syncWithCloud(true);
    }
  }

  function formatDate(ts: number) {
    if (!ts) return '從未同步';
    return new Date(ts).toLocaleString('zh-TW', {
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
</script>

<div class="flex items-center gap-2 relative">
  {#if auth.user}
    <div class="hidden sm:flex items-center gap-2 px-2 py-1 rounded-full bg-surface-secondary border border-border">
      {#if auth.user.photoURL}
        <img src={auth.user.photoURL} alt="Avatar" class="w-5 h-5 rounded-full border border-border" />
      {/if}
      <span class="text-[11px] font-medium text-content-secondary truncate max-w-20">{auth.user.displayName || '使用者'}</span>
      <button 
        onclick={() => auth.logout()}
        class="p-1 rounded-full hover:bg-srs-again/10 text-content-tertiary hover:text-srs-again transition-colors"
        title="登出"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
      </button>
    </div>
  {/if}

  <div class="relative">
    <button
      onclick={handleSync}
      disabled={sync.status === 'syncing'}
      class="mode-btn p-2 rounded-lg transition-all relative group flex items-center gap-1.5"
      class:active={sync.status === 'syncing'}
      title={auth.user ? `立即同步 (上次同步: ${formatDate(sync.lastSyncTime)})` : "登入 Google 以同步"}
    >
      {#if sync.status === 'syncing'}
        <div class="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin"></div>
      {:else if auth.user}
        <!-- Traffic light status dot -->
        <div 
          class="w-1.5 h-1.5 rounded-full transition-colors shadow-sm"
          class:bg-srs-good={!isStale && sync.status !== 'error'}
          class:bg-srs-hard={isStale && sync.status !== 'error'}
          class:bg-srs-again={sync.status === 'error'}
        ></div>

        <!-- Sync icon -->
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-content-tertiary group-hover:text-content-secondary transition-colors" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
          <path d="M20 12a8 8 0 1 1-8-8c2.24 0 4.38.89 5.99 2.44L20 8" />
          <path d="M20 3v5h-5" />
        </svg>
      {:else}
        <!-- Login icon -->
        <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-content-tertiary" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
          <path d="M12 13v8" />
          <path d="m15 16-3-3-3 3" />
          <path d="M20 16.2A4.5 4.5 0 0 0 17.5 8h-1.8A7 7 0 1 0 4 14.9" />
        </svg>
      {/if}
    </button>

    {#if sync.status === 'error' && showErrorPopover}
      <div 
        class="absolute top-full right-0 mt-2 w-72 p-4 bg-surface-primary border border-border rounded-xl shadow-2xl z-50 origin-top-right"
        in:fade={{ duration: 150 }}
      >
        <div class="flex items-start gap-3">
          <div class="shrink-0 w-8 h-8 rounded-full bg-srs-again/10 flex items-center justify-center text-srs-again">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          </div>
          <div class="flex-1 min-w-0">
            <h4 class="text-sm font-bold text-content-primary mb-1">
              {sync.lastSyncError?.includes('頻繁') ? '同步冷卻中' : '同步發生錯誤'}
            </h4>
            <p class="text-xs text-content-secondary leading-relaxed wrap-break-word">
              {sync.lastSyncError || '連線至雲端時發生問題，請檢查網路狀態或稍後再試。'}
            </p>
            <div class="mt-3 flex items-center gap-3">
              <button 
                onclick={() => { showErrorPopover = false; handleSync(); }}
                class="text-xs font-bold text-accent hover:text-accent-hover transition-colors"
              >
                重新嘗試
              </button>
              <button 
                onclick={() => showErrorPopover = false}
                class="text-xs font-medium text-content-tertiary hover:text-content-secondary transition-colors"
              >
                關閉
              </button>
            </div>
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>

{#if showConflictDialog && conflictData}
  <div class="fixed inset-0 z-100 flex items-center justify-center p-4 bg-black/40 backdrop-blur-[2px]">
    <div class="bg-surface-primary p-6 rounded-2xl shadow-2xl border border-border max-w-sm w-full" in:fade={{ duration: 200 }}>
      <div class="w-12 h-12 rounded-full bg-accent/10 flex items-center justify-center text-accent mb-4">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 21 1.9-1.9"/><path d="m3 3 1.9 1.9"/><path d="M5 16a9 9 0 0 1 0-8"/><path d="M9 19c.5 0 1.1.1 1.1.1"/><path d="M9 5c.5 0 1.1-.1 1.1-.1"/><path d="M15 19c-.5 0-1.1.1-1.1.1"/><path d="M15 5c-.5 0-1.1-.1-1.1-.1"/><path d="m19 19 2 2"/><path d="m19 5 2-2"/><path d="M19 16a9 9 0 0 0 0-8"/></svg>
      </div>
      <h3 class="text-lg font-bold text-content-primary mb-2">同步衝突</h3>
      <p class="text-sm text-content-secondary mb-6 leading-relaxed">
        雲端資料比本機端資料新。為了確保學習進度不遺失，請選擇要保留的版本。
      </p>
      
      <div class="space-y-3 mb-8">
        <button 
          onclick={() => resolveConflict(true)}
          class="w-full p-4 rounded-xl border-2 border-border hover:border-accent bg-surface-secondary transition-all text-left group"
        >
          <div class="flex justify-between items-center mb-1">
            <span class="text-[10px] font-bold text-content-tertiary uppercase tracking-widest">雲端版本 (較新)</span>
            <div class="w-2 h-2 rounded-full bg-srs-good opacity-0 group-hover:opacity-100 transition-opacity"></div>
          </div>
          <p class="text-sm text-content-primary font-bold">{formatDate(conflictData.cloudTime)}</p>
          <p class="text-[11px] text-content-tertiary mt-1">這將會覆蓋您目前的本機端進度</p>
        </button>

        <button 
          onclick={() => showConflictDialog = false}
          class="w-full p-4 rounded-xl border-2 border-transparent hover:border-border bg-surface-page transition-all text-left group"
        >
          <div class="flex justify-between items-center mb-1">
            <span class="text-[10px] font-bold text-content-tertiary uppercase tracking-widest">本機端版本</span>
          </div>
          <p class="text-sm text-content-primary font-bold">{formatDate(conflictData.localTime)}</p>
          <p class="text-[11px] text-content-tertiary mt-1">暫時保留目前進度，稍後再手動同步</p>
        </button>
      </div>

      <div class="flex flex-col gap-2">
        <button 
          onclick={() => resolveConflict(true)}
          class="w-full py-3 bg-accent text-white rounded-xl font-bold hover:bg-accent-hover transition-all shadow-lg shadow-accent/20 active:scale-[0.98]"
        >
          確認使用雲端版本
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .text-srs-again { color: var(--color-srs-again); }
  .bg-srs-again { background-color: var(--color-srs-again); }
  .bg-srs-good { background-color: var(--color-srs-good); }
  .bg-srs-hard { background-color: var(--color-srs-hard); }
  
  .mode-btn {
    color: var(--color-content-tertiary);
  }
  .mode-btn:hover {
    background-color: var(--color-surface-hover);
    color: var(--color-content-secondary);
  }
  .mode-btn.active {
    color: var(--color-accent);
  }
</style>
