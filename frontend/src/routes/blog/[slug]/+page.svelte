<script lang="ts">
    import type { PageData } from "./$types";
    import type { Component } from "svelte";
    import { browser } from "$app/environment";
    import { base } from "$app/paths";
    import { page } from "$app/stores";
    import TableOfContents from "$lib/components/blog/TableOfContents.svelte";

    let { data }: { data: PageData } = $props();

    const metadata = $derived(data.metadata);
    const Content = $derived(data.content as Component);
    const canonicalUrl = $derived(`${$page.url.origin}${base}/blog/${metadata.slug}`);

    let showMobileToc = $state(false);
</script>

<svelte:head>
    <title>{metadata.title} | 學測高頻單字</title>
    <meta name="title" content="{metadata.title} | 學測高頻單字" />
    <meta name="description" content={metadata.description} />
    <link rel="canonical" href={canonicalUrl} />

    <meta property="og:title" content="{metadata.title} | 學測高頻單字" />
    <meta property="og:description" content={metadata.description} />
    <meta property="og:url" content={canonicalUrl} />
    <meta property="og:type" content="article" />

    {@html `<script type="application/ld+json">${JSON.stringify({
        "@context": "https://schema.org",
        "@type": "Article",
        headline: metadata.title,
        description: metadata.description,
        datePublished: metadata.date,
        dateModified: metadata.updated || metadata.date,
        author: { "@type": "Organization", name: "學測高頻單字" },
        publisher: { "@type": "Organization", name: "學測高頻單字" },
        mainEntityOfPage: {
            "@type": "WebPage",
            "@id": canonicalUrl,
        },
    })}</script>`}
</svelte:head>

<div class="article-page">
    <div class="layout">
        <article class="article">
            <header class="header">
                <a href="{base}/blog" class="back">← 學習資源</a>
                <h1>{metadata.title}</h1>
                <div class="meta">
                    <time datetime={metadata.date}>
                        {new Date(metadata.date).toLocaleDateString("zh-TW", {
                            year: "numeric",
                            month: "long",
                            day: "numeric",
                        })}
                    </time>
                    {#if metadata.reading_time}
                        <span>·</span>
                        <span>{metadata.reading_time} 分鐘</span>
                    {/if}
                </div>
            </header>

            <div class="content">
                <Content />
            </div>

            <div class="cta-section">
                <div class="cta-card">
                    <div class="cta-text">
                        <h3>開始練習</h3>
                        <p>用科學方法背單字，免費、不收集資料</p>
                    </div>
                    <div class="cta-buttons">
                        <a href="{base}/flashcard" class="cta-btn primary">字卡複習</a
                        >
                        <a href="{base}/quiz" class="cta-btn secondary">單字測驗</a>
                    </div>
                </div>
            </div>

            <footer class="footer">
                <p class="image-credit">
                    本文圖片來源：<a
                        href="https://unsplash.com"
                        target="_blank"
                        rel="noopener">Unsplash</a
                    >
                </p>
                <a href="{base}/blog" class="back-btn">← 返回文章列表</a>
            </footer>
        </article>

        <aside class="sidebar">
            {#if browser}
                <TableOfContents />
            {/if}
        </aside>
    </div>

    <!-- Mobile TOC -->
    {#if browser}
        <button
            class="mobile-toc-btn"
            onclick={() => (showMobileToc = !showMobileToc)}
            aria-label="目錄"
        >
            <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke-width="1.5"
                stroke="currentColor"
                class="icon"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25H12"
                />
            </svg>
        </button>

        {#if showMobileToc}
            <div
                class="mobile-toc-overlay"
                onclick={() => (showMobileToc = false)}
                role="presentation"
            ></div>
            <div class="mobile-toc-sheet">
                <div class="mobile-toc-header">
                    <span>目錄</span>
                    <button
                        onclick={() => (showMobileToc = false)}
                        aria-label="關閉"
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke-width="1.5"
                            stroke="currentColor"
                            class="icon"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M6 18 18 6M6 6l12 12"
                            />
                        </svg>
                    </button>
                </div>
                <div
                    class="mobile-toc-content"
                    onclick={() => (showMobileToc = false)}
                    role="presentation"
                >
                    <TableOfContents />
                </div>
            </div>
        {/if}
    {/if}
</div>

<style>
    .article-page {
        min-height: 100%;
        padding: 2rem 1rem;
        padding-bottom: calc(3rem + var(--bottom-nav-height, 0px));
    }

    .layout {
        max-width: 1000px;
        margin: 0 auto;
        display: grid;
        grid-template-columns: 1fr;
        gap: 3rem;
    }

    .article {
        max-width: 680px;
        margin: 0 auto;
        width: 100%;
    }

    .sidebar {
        display: none;
    }

    @media (min-width: 1024px) {
        .layout {
            grid-template-columns: 1fr 200px;
        }

        .article {
            margin: 0;
        }

        .sidebar {
            display: block;
        }
    }

    .header {
        margin-bottom: 2rem;
    }

    .back {
        display: inline-block;
        font-size: 0.875rem;
        color: var(--color-content-secondary);
        text-decoration: none;
        margin-bottom: 1rem;
    }

    .back:hover {
        color: var(--color-content-primary);
    }

    .header h1 {
        font-size: 1.75rem;
        font-weight: 700;
        color: var(--color-content-primary);
        line-height: 1.3;
        margin: 0 0 0.75rem;
        letter-spacing: -0.02em;
    }

    .meta {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.875rem;
        color: var(--color-content-tertiary);
    }

    @media (min-width: 640px) {
        .header h1 {
            font-size: 2rem;
        }
    }

    /* Content Prose Styles */
    .content {
        font-size: 1rem;
        line-height: 1.75;
        color: var(--color-content-primary);
    }

    .content :global(h2) {
        font-size: 1.375rem;
        font-weight: 600;
        margin: 2.5rem 0 1rem;
        color: var(--color-content-primary);
        letter-spacing: -0.01em;
    }

    .content :global(h2 a) {
        color: inherit;
        text-decoration: none;
    }

    .content :global(h3) {
        font-size: 1.125rem;
        font-weight: 600;
        margin: 2rem 0 0.75rem;
        color: var(--color-content-primary);
    }

    .content :global(h3 a) {
        color: inherit;
        text-decoration: none;
    }

    .content :global(h4) {
        font-size: 1rem;
        font-weight: 600;
        margin: 1.5rem 0 0.5rem;
        color: var(--color-content-primary);
    }

    .content :global(p) {
        margin: 0 0 1.25rem;
    }

    .content :global(ul) {
        margin: 0 0 1.25rem;
        padding-left: 1.25rem;
        list-style-type: disc;
    }

    .content :global(ol) {
        margin: 0 0 1.25rem;
        padding-left: 1.25rem;
        list-style-type: decimal;
    }

    .content :global(li) {
        margin-bottom: 0.375rem;
        padding-left: 0.25rem;
    }

    .content :global(li::marker) {
        color: var(--color-content-tertiary);
    }

    .content :global(blockquote) {
        margin: 1.5rem 0;
        padding: 0.75rem 1rem;
        border-left: 3px solid var(--color-border-hover);
        background: var(--color-surface-secondary);
        border-radius: 0 6px 6px 0;
    }

    .content :global(blockquote p) {
        margin: 0;
        color: var(--color-content-secondary);
    }

    .content :global(code) {
        font-family:
            ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 0.875em;
        padding: 0.125rem 0.375rem;
        background: var(--color-surface-secondary);
        border-radius: 4px;
        color: var(--color-content-primary);
    }

    .content :global(pre) {
        margin: 1.5rem 0;
        padding: 1rem;
        background: var(--color-surface-secondary);
        border-radius: 8px;
        overflow-x: auto;
    }

    .content :global(pre code) {
        padding: 0;
        background: none;
    }

    .content :global(a) {
        color: var(--color-accent);
        text-decoration: underline;
        text-underline-offset: 2px;
    }

    .content :global(a:hover) {
        text-decoration-thickness: 2px;
    }

    .content :global(strong) {
        font-weight: 600;
        color: var(--color-content-primary);
    }

    .content :global(hr) {
        border: none;
        border-top: 1px solid var(--color-border);
        margin: 2rem 0;
    }

    .content :global(table) {
        width: 100%;
        border-collapse: collapse;
        margin: 1.5rem 0;
        font-size: 0.9375rem;
    }

    .content :global(th),
    .content :global(td) {
        padding: 0.625rem 0.75rem;
        text-align: left;
        border-bottom: 1px solid var(--color-border);
    }

    .content :global(th) {
        font-weight: 600;
        color: var(--color-content-primary);
        background: var(--color-surface-secondary);
    }

    .content :global(tr:last-child td) {
        border-bottom: none;
    }

    /* CTA Section */
    .cta-section {
        margin-top: 3rem;
    }

    .cta-card {
        display: flex;
        flex-direction: column;
        gap: 1.25rem;
        padding: 1.5rem;
        background: var(--color-surface-secondary);
        border: 1px solid var(--color-border);
        border-radius: 12px;
    }

    .cta-text h3 {
        font-size: 1.125rem;
        font-weight: 600;
        color: var(--color-content-primary);
        margin: 0 0 0.25rem;
    }

    .cta-text p {
        font-size: 0.875rem;
        color: var(--color-content-secondary);
        margin: 0;
    }

    .cta-buttons {
        display: flex;
        gap: 0.75rem;
    }

    .cta-btn {
        flex: 1;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.625rem 1rem;
        font-size: 0.875rem;
        font-weight: 500;
        text-decoration: none;
        border-radius: 8px;
        transition: all 0.15s ease;
    }

    .cta-btn.primary {
        background: var(--color-accent);
        color: white;
    }

    .cta-btn.primary:hover {
        filter: brightness(1.1);
    }

    .cta-btn.secondary {
        background: var(--color-surface-primary);
        color: var(--color-content-primary);
        border: 1px solid var(--color-border);
    }

    .cta-btn.secondary:hover {
        border-color: var(--color-border-hover);
        background: var(--color-surface-secondary);
    }

    @media (min-width: 480px) {
        .cta-card {
            flex-direction: row;
            align-items: center;
            justify-content: space-between;
        }

        .cta-buttons {
            flex: 0 0 auto;
        }

        .cta-btn {
            flex: 0 0 auto;
        }
    }

    .footer {
        margin-top: 3rem;
        padding-top: 1.5rem;
        border-top: 1px solid var(--color-border);
    }

    .image-credit {
        font-size: 0.8125rem;
        color: var(--color-content-tertiary);
        margin: 0 0 1rem;
    }

    .image-credit a {
        color: var(--color-content-secondary);
        text-decoration: underline;
        text-underline-offset: 2px;
    }

    .back-btn {
        font-size: 0.875rem;
        color: var(--color-content-secondary);
        text-decoration: none;
    }

    .back-btn:hover {
        color: var(--color-content-primary);
    }

    /* Mobile TOC */
    .mobile-toc-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        position: fixed;
        bottom: 1.5rem;
        right: 1rem;
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: var(--color-surface-primary);
        border: 1px solid var(--color-border);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        cursor: pointer;
        z-index: 40;
    }

    .mobile-toc-btn .icon {
        width: 20px;
        height: 20px;
        color: var(--color-content-primary);
    }

    @media (min-width: 1024px) {
        .mobile-toc-btn {
            display: none;
        }
    }

    .mobile-toc-overlay {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.3);
        z-index: 50;
    }

    .mobile-toc-sheet {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        max-height: 60vh;
        background: var(--color-surface-primary);
        border-radius: 16px 16px 0 0;
        z-index: 51;
        display: flex;
        flex-direction: column;
    }

    .mobile-toc-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1rem 1.25rem;
        border-bottom: 1px solid var(--color-border);
        font-weight: 600;
        color: var(--color-content-primary);
    }

    .mobile-toc-header button {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border: none;
        background: none;
        cursor: pointer;
        border-radius: 6px;
    }

    .mobile-toc-header button:hover {
        background: var(--color-surface-secondary);
    }

    .mobile-toc-header .icon {
        width: 20px;
        height: 20px;
        color: var(--color-content-secondary);
    }

    .mobile-toc-content {
        padding: 1rem 1.25rem;
        overflow-y: auto;
    }
</style>
