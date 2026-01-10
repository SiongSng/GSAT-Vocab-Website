<script lang="ts">
    import type { PageData } from "./$types";
    import { base } from "$app/paths";
    import { page } from "$app/stores";

    let { data }: { data: PageData } = $props();

    const canonicalUrl = $derived(`${$page.url.origin}${base}/blog`);
    const title = "學習資源 | 學測高頻單字";
    const description = "學測英文準備攻略、背單字方法、混淆詞比較等實用文章。";

    const categoryLabels: Record<string, string> = {
        "learning-strategy": "學習方法",
        vocabulary: "單字學習",
        "exam-strategy": "考試策略",
        "study-plan": "讀書計畫",
        parents: "家長專區",
    };
</script>

<svelte:head>
    <title>{title}</title>
    <meta name="title" content={title} />
    <meta name="description" content={description} />
    <link rel="canonical" href={canonicalUrl} />

    <meta property="og:title" content={title} />
    <meta property="og:description" content={description} />
    <meta property="og:url" content={canonicalUrl} />

    {@html `<script type="application/ld+json">${JSON.stringify({
        "@context": "https://schema.org",
        "@type": "Blog",
        name: "學測高頻單字 - 學習資源",
        url: canonicalUrl,
        description: description,
        inLanguage: "zh-TW",
    })}</script>`}
</svelte:head>

<div class="blog-page">
    <header class="hero">
        <div class="hero-content">
            <h1>學習資源</h1>
            <p class="hero-desc">學測英文準備心法、背單字技巧、常見問題解答</p>
        </div>
    </header>

    <main class="main">
        <div class="container">
            {#if data.posts.length === 0}
                <div class="empty-state">
                    <p>文章即將推出</p>
                </div>
            {:else}
                <div class="posts-grid">
                    {#each data.posts as post, i}
                        <a
                            href="{base}/blog/{post.slug}"
                            class="post-card"
                            class:featured={i === 0}
                        >
                            {#if post.image}
                                <div class="card-image">
                                    <img
                                        src="{base}{post.image}"
                                        alt=""
                                        loading="lazy"
                                    />
                                </div>
                            {/if}
                            <div class="card-content">
                                <div class="card-meta">
                                    <span class="category"
                                        >{categoryLabels[post.category] ||
                                            post.category}</span
                                    >
                                    <span class="reading-time"
                                        >{post.reading_time} 分鐘</span
                                    >
                                </div>
                                <h2 class="card-title">{post.title}</h2>
                                <p class="card-desc">{post.description}</p>
                            </div>
                        </a>
                    {/each}
                </div>
            {/if}
        </div>
    </main>
</div>

<style>
    .blog-page {
        min-height: 100%;
        padding-bottom: calc(2rem + var(--bottom-nav-height, 0px));
    }

    .hero {
        padding: 3rem 1.5rem 2.5rem;
        border-bottom: 1px solid var(--color-border);
    }

    .hero-content {
        max-width: 800px;
        margin: 0 auto;
    }

    .hero h1 {
        font-size: 2rem;
        font-weight: 700;
        color: var(--color-content-primary);
        margin: 0 0 0.5rem;
        letter-spacing: -0.02em;
    }

    .hero-desc {
        font-size: 1.0625rem;
        color: var(--color-content-secondary);
        margin: 0;
        line-height: 1.5;
    }

    .main {
        padding: 2rem 1.5rem;
    }

    .container {
        max-width: 800px;
        margin: 0 auto;
    }

    .empty-state {
        padding: 4rem 0;
        text-align: center;
        color: var(--color-content-tertiary);
    }

    .posts-grid {
        display: grid;
        gap: 1.5rem;
    }

    .post-card {
        display: flex;
        flex-direction: column;
        background: var(--color-surface-primary);
        border: 1px solid var(--color-border);
        border-radius: 12px;
        text-decoration: none;
        transition: all 0.2s ease;
        overflow: hidden;
    }

    .post-card:hover {
        border-color: var(--color-border-hover);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
        transform: translateY(-2px);
    }

    .card-image {
        aspect-ratio: 16 / 9;
        overflow: hidden;
        background: var(--color-surface-secondary);
    }

    .card-image img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        transition: transform 0.3s ease;
    }

    .post-card:hover .card-image img {
        transform: scale(1.03);
    }

    .card-content {
        padding: 1.25rem;
    }

    .card-meta {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 0.5rem;
    }

    .category {
        font-size: 0.75rem;
        font-weight: 500;
        color: var(--color-content-secondary);
    }

    .reading-time {
        font-size: 0.75rem;
        color: var(--color-content-tertiary);
    }

    .reading-time::before {
        content: "·";
        margin-right: 0.75rem;
    }

    .card-title {
        font-size: 1.0625rem;
        font-weight: 600;
        color: var(--color-content-primary);
        margin: 0 0 0.375rem;
        line-height: 1.4;
        letter-spacing: -0.01em;
    }

    .card-desc {
        font-size: 0.875rem;
        color: var(--color-content-secondary);
        margin: 0;
        line-height: 1.55;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    @media (min-width: 640px) {
        .hero {
            padding: 4rem 2rem 3rem;
        }

        .hero h1 {
            font-size: 2.5rem;
        }

        .hero-desc {
            font-size: 1.125rem;
        }

        .main {
            padding: 2.5rem 2rem;
        }

        .posts-grid {
            grid-template-columns: repeat(2, 1fr);
            gap: 1.5rem;
        }

        .post-card.featured {
            grid-column: span 2;
            flex-direction: row;
        }

        .post-card.featured .card-image {
            flex: 0 0 45%;
            aspect-ratio: auto;
        }

        .post-card.featured .card-content {
            flex: 1;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .post-card.featured .card-title {
            font-size: 1.375rem;
        }

        .post-card.featured .card-desc {
            -webkit-line-clamp: 3;
        }

        .card-content {
            padding: 1.25rem;
        }

        .card-title {
            font-size: 1.125rem;
        }
    }
</style>
