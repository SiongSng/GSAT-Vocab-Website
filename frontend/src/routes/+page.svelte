<script lang="ts">
    import BrowseView from "$lib/components/BrowseView.svelte";

    const BASE_URL = "https://siongsng.github.io/GSAT-Vocab-Website";
    const title = "學測英文高頻單字";
    const description = "從歷屆學測試題萃取 5000+ 高頻單字，提供智慧複習、詞頻統計與字根拆解功能。";
</script>

<svelte:head>
    <title>{title}</title>
    <meta name="title" content={title} />
    <meta name="description" content={description} />
    <link rel="canonical" href="{BASE_URL}/" />

    <!-- Open Graph -->
    <meta property="og:type" content="website" />
    <meta property="og:locale" content="zh_TW" />
    <meta property="og:site_name" content="學測英文高頻單字" />
    <meta property="og:url" content="{BASE_URL}/" />
    <meta property="og:title" content={title} />
    <meta property="og:description" content={description} />
    <meta property="og:image" content="{BASE_URL}/og-image.png" />
    <meta property="og:image:width" content="1200" />
    <meta property="og:image:height" content="630" />

    <!-- Twitter -->
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content={title} />
    <meta name="twitter:description" content={description} />
    <meta name="twitter:image" content="{BASE_URL}/og-image.png" />

    <!-- Structured Data -->
    {@html `<script type="application/ld+json">${JSON.stringify({
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "學測英文高頻單字",
        "alternateName": ["GSAT Vocab", "學測單字", "學測高頻單字"],
        "url": BASE_URL + "/",
        "description": description,
        "inLanguage": "zh-TW",
        "potentialAction": {
            "@type": "SearchAction",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": BASE_URL + "/word/{search_term_string}"
            },
            "query-input": "required name=search_term_string"
        }
    })}</script>`}

    {@html `<script type="application/ld+json">${JSON.stringify({
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "name": "學測英文高頻單字",
        "url": BASE_URL + "/",
        "description": description,
        "applicationCategory": "EducationalApplication",
        "operatingSystem": "Any",
        "browserRequirements": "Requires JavaScript",
        "softwareVersion": "1.0.0",
        "offers": {
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "TWD"
        },
        "featureList": [
            "5000+ 學測高頻單字",
            "智慧間隔複習排程",
            "詞頻統計分析",
            "字根字首拆解",
            "離線使用支援"
        ],
        "screenshot": BASE_URL + "/og-image.png",
        "inLanguage": "zh-TW",
        "audience": {
            "@type": "EducationalAudience",
            "educationalRole": "student",
            "audienceType": "高中生"
        },
        "educationalLevel": "高中",
        "learningResourceType": "單字學習工具"
    })}</script>`}

    {@html `<script type="application/ld+json">${JSON.stringify({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [{
            "@type": "ListItem",
            "position": 1,
            "name": "首頁",
            "item": BASE_URL + "/"
        }]
    })}</script>`}

    {@html `<script type="application/ld+json">${JSON.stringify({
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "學測英文高頻單字",
        "url": BASE_URL + "/",
        "logo": BASE_URL + "/pwa-512x512.png",
        "description": description,
        "sameAs": ["https://github.com/siongsng/GSAT-Vocab-Website"]
    })}</script>`}
</svelte:head>

<BrowseView />
