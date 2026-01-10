<script lang="ts">
    import { onMount } from "svelte";
    import { browser } from "$app/environment";
    import { base } from "$app/paths";
    import type { PageData } from "./$types";
    import type { WordEntry } from "$lib/types/vocab";
    import EntryDetailContent from "$lib/components/word/EntryDetailContent.svelte";
    import BrowseView from "$lib/components/BrowseView.svelte";
    import { selectWord, loadVocabData } from "$lib/stores/vocab.svelte";
    import { getAppStore } from "$lib/stores/app.svelte";

    let { data }: { data: PageData } = $props();

    const app = getAppStore();
    const BASE_URL = "https://siongsng.github.io/GSAT-Vocab-Website";

    const word = $derived(data.word as WordEntry);
    const title = $derived(`${word.lemma} 是什麼意思？例句、用法一次搞懂`);
    const primaryDef = $derived(word.senses?.[0]?.zh_def || "");
    const importancePercent = $derived(
        Math.round((word.frequency?.importance_score ?? 0) * 100)
    );
    const testedCount = $derived(word.frequency?.tested_count ?? 0);

    const description = $derived(() => {
        const parts: string[] = [];
        parts.push(`${word.lemma} 中文意思是「${primaryDef}」`);
        if (testedCount > 0) {
            parts.push(`學測出現過 ${testedCount} 次`);
        }
        if (importancePercent > 50) {
            parts.push(`重要程度 ${importancePercent}%`);
        }
        parts.push("看例句學用法，輕鬆記住這個單字！");
        return parts.join("，");
    });

    onMount(() => {
        if (browser) {
            loadVocabData().then(() => {
                selectWord(data.lemma);
            });
        }
    });
</script>

<svelte:head>
    <title>{title}</title>
    <meta name="title" content={title} />
    <meta name="description" content={description()} />
    <link rel="canonical" href="{BASE_URL}/word/{encodeURIComponent(word.lemma)}" />

    <meta property="og:title" content={title} />
    <meta property="og:description" content={description()} />
    <meta property="og:url" content="{BASE_URL}/word/{encodeURIComponent(word.lemma)}" />
    <meta property="og:type" content="article" />

    <meta name="twitter:title" content={title} />
    <meta name="twitter:description" content={description()} />

    {@html `<script type="application/ld+json">${JSON.stringify({
        "@context": "https://schema.org",
        "@type": "DefinedTerm",
        "@id": `${BASE_URL}/word/${encodeURIComponent(word.lemma)}`,
        "name": word.lemma,
        "description": word.senses?.map(s => s.zh_def).join("; ") || "",
        "inDefinedTermSet": {
            "@type": "DefinedTermSet",
            "name": "學測高頻單字資料庫",
            "url": BASE_URL
        },
        "termCode": word.pos?.join(", ") || ""
    })}</script>`}

    {@html `<script type="application/ld+json">${JSON.stringify({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            { "@type": "ListItem", "position": 1, "name": "首頁", "item": BASE_URL + "/" },
            { "@type": "ListItem", "position": 2, "name": word.lemma, "item": `${BASE_URL}/word/${encodeURIComponent(word.lemma)}` }
        ]
    })}</script>`}
</svelte:head>

{#if app.isMobile === false}
    <BrowseView />
{:else if app.isMobile === true}
    <div class="word-page h-full overflow-y-auto bg-surface-page relative">
        <a
            href="{base}/"
            class="back-btn-float"
            aria-label="返回首頁"
        >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
            </svg>
        </a>
        <div class="detail-content p-6 pt-14">
            <EntryDetailContent entry={word} />
        </div>
    </div>
{:else}
    <!-- SSR: 顯示完整 SEO 內容 -->
    <div class="word-page h-full overflow-y-auto bg-surface-page">
        <div class="detail-content p-6 lg:p-8">
            <EntryDetailContent entry={word} />
        </div>
    </div>
{/if}

<style>
    .word-page {
        display: flex;
        flex-direction: column;
    }

    .back-btn-float {
        position: fixed;
        top: calc(4.5rem + env(safe-area-inset-top, 0px));
        left: calc(env(safe-area-inset-left, 0px) + 0.75rem);
        padding: 0.5rem;
        border-radius: 0.375rem;
        background-color: rgba(var(--color-surface-primary-rgb, 255, 255, 255), 0.8);
        backdrop-filter: blur(4px);
        border: 1px solid var(--color-border);
        z-index: 50;
        transition: background-color 0.15s ease;
        color: var(--color-content-secondary);
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .back-btn-float:hover {
        background-color: var(--color-surface-hover);
    }

    .word-page::-webkit-scrollbar {
        width: 6px;
    }

    .word-page::-webkit-scrollbar-track {
        background: transparent;
    }

    .word-page::-webkit-scrollbar-thumb {
        background-color: var(--color-border-hover);
        border-radius: 3px;
    }
</style>
