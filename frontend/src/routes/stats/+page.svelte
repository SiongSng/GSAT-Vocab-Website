<script lang="ts">
    import StatsView from "$lib/components/stats/StatsView.svelte";

    const BASE_URL = "https://siongsng.github.io/GSAT-Vocab-Website";
    const title = "學習統計 | 學測高頻單字";
    const description = "查看你的學習進度、複習統計和學習成效分析。";
</script>

<svelte:head>
    <title>{title}</title>
    <meta name="title" content={title} />
    <meta name="description" content={description} />
    <link rel="canonical" href="{BASE_URL}/stats" />

    <meta property="og:title" content={title} />
    <meta property="og:description" content={description} />
    <meta property="og:url" content="{BASE_URL}/stats" />

    {@html `<script type="application/ld+json">${JSON.stringify({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            { "@type": "ListItem", "position": 1, "name": "首頁", "item": BASE_URL + "/" },
            { "@type": "ListItem", "position": 2, "name": "學習統計", "item": BASE_URL + "/stats" }
        ]
    })}</script>`}
</svelte:head>

<StatsView />
