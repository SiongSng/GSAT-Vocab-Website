import type { PageLoad, EntryGenerator } from './$types';
import { error } from '@sveltejs/kit';

interface BlogMetadata {
    title: string;
    slug: string;
    description: string;
    date: string;
    updated?: string;
    category: string;
    tags: string[];
    image?: string;
    reading_time?: number;
}

const posts = import.meta.glob('/content/blog/*.md', { eager: true });

export const load: PageLoad = async ({ params }) => {
    const path = `/content/blog/${params.slug}.md`;
    const post = posts[path] as { default: unknown; metadata: BlogMetadata } | undefined;

    if (!post) {
        throw error(404, `找不到文章: ${params.slug}`);
    }

    return {
        content: post.default,
        metadata: { ...post.metadata, slug: params.slug } as BlogMetadata
    };
};

export const entries: EntryGenerator = async () => {
    return Object.keys(posts).map(path => ({
        slug: path.split('/').pop()?.replace('.md', '') || ''
    }));
};

export const prerender = true;
