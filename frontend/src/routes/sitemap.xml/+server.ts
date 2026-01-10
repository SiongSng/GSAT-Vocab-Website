import type { RequestHandler } from './$types';

const BASE_URL = 'https://siongsng.github.io/GSAT-Vocab-Website';

export const prerender = true;

export const GET: RequestHandler = async ({ fetch }) => {
    const now = new Date().toISOString().split('T')[0];

    const staticPages = [
        { url: '/', priority: '1.0', changefreq: 'daily' },
        { url: '/flashcard', priority: '0.8', changefreq: 'weekly' },
        { url: '/quiz', priority: '0.8', changefreq: 'weekly' },
        { url: '/stats', priority: '0.5', changefreq: 'weekly' },
        { url: '/blog', priority: '0.9', changefreq: 'daily' },
    ];

    let wordUrls: string[] = [];
    try {
        const indexRes = await fetch('/data/index.json');
        if (indexRes.ok) {
            const words = await indexRes.json() as Array<{ lemma: string }>;
            wordUrls = words.map(w => {
                const encodedLemma = encodeURIComponent(w.lemma);
                return `
    <url>
        <loc>${BASE_URL}/word/${encodedLemma}</loc>
        <lastmod>${now}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.6</priority>
    </url>`;
            });
        }
    } catch {
        console.warn('Could not load word index for sitemap');
    }

    let blogUrls: string[] = [];
    try {
        const posts = import.meta.glob('/content/blog/*.md', { eager: true });
        blogUrls = Object.entries(posts).map(([path, module]) => {
            const slug = path.split('/').pop()?.replace('.md', '') || '';
            const metadata = (module as { metadata: { date: string; updated?: string } }).metadata;
            const lastmod = metadata.updated || metadata.date || now;
            return `
    <url>
        <loc>${BASE_URL}/blog/${slug}</loc>
        <lastmod>${lastmod}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.7</priority>
    </url>`;
        });
    } catch {
        console.warn('Could not load blog posts for sitemap');
    }

    const staticUrls = staticPages.map(p => `
    <url>
        <loc>${BASE_URL}${p.url}</loc>
        <lastmod>${now}</lastmod>
        <changefreq>${p.changefreq}</changefreq>
        <priority>${p.priority}</priority>
    </url>`);

    const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${staticUrls.join('')}
${blogUrls.join('')}
${wordUrls.join('')}
</urlset>`;

    return new Response(sitemap.trim(), {
        headers: {
            'Content-Type': 'application/xml',
            'Cache-Control': 'max-age=3600'
        }
    });
};
