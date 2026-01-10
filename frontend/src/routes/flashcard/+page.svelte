<script lang="ts">
    import SRSFlashcardView from "$lib/components/srs/SRSFlashcardView.svelte";

    const BASE_URL = "https://siongsng.github.io/GSAT-Vocab-Website";
    const title = "單字卡複習 | 學測高頻單字";
    const description = "間隔記憶演算法智慧安排複習時程，依遺忘曲線科學化背單字，學習效率倍增。";
</script>

<svelte:head>
    <title>{title}</title>
    <meta name="title" content={title} />
    <meta name="description" content={description} />
    <link rel="canonical" href="{BASE_URL}/flashcard" />

    <meta property="og:title" content={title} />
    <meta property="og:description" content={description} />
    <meta property="og:url" content="{BASE_URL}/flashcard" />

    <meta name="twitter:title" content={title} />
    <meta name="twitter:description" content={description} />

    {@html `<script type="application/ld+json">${JSON.stringify({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            { "@type": "ListItem", "position": 1, "name": "首頁", "item": BASE_URL + "/" },
            { "@type": "ListItem", "position": 2, "name": "單字卡複習", "item": BASE_URL + "/flashcard" }
        ]
    })}</script>`}
</svelte:head>

<SRSFlashcardView />
