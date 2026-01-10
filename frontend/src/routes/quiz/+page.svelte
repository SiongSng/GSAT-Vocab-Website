<script lang="ts">
    import QuizView from "$lib/components/QuizView.svelte";

    const BASE_URL = "https://siongsng.github.io/GSAT-Vocab-Website";
    const title = "測驗模式 | 學測高頻單字";
    const description = "多元題型測驗單字掌握程度，即時回饋學習成效，精準找出需加強的弱點單字。";
</script>

<svelte:head>
    <title>{title}</title>
    <meta name="title" content={title} />
    <meta name="description" content={description} />
    <link rel="canonical" href="{BASE_URL}/quiz" />

    <meta property="og:title" content={title} />
    <meta property="og:description" content={description} />
    <meta property="og:url" content="{BASE_URL}/quiz" />

    <meta name="twitter:title" content={title} />
    <meta name="twitter:description" content={description} />

    {@html `<script type="application/ld+json">${JSON.stringify({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            { "@type": "ListItem", "position": 1, "name": "首頁", "item": BASE_URL + "/" },
            { "@type": "ListItem", "position": 2, "name": "測驗模式", "item": BASE_URL + "/quiz" }
        ]
    })}</script>`}
</svelte:head>

<QuizView />
