import type { PageLoad } from './$types';

interface BlogPost {
    slug: string;
    title: string;
    description: string;
    date: string;
    category: string;
    tags: string[];
    reading_time?: number;
    featured?: boolean;
    image?: string;
}

export const load: PageLoad = async () => {
    const postModules = import.meta.glob('/content/blog/*.md', { eager: true });

    const posts: BlogPost[] = Object.entries(postModules).map(([path, module]) => {
        const m = module as { metadata: BlogPost };
        const slug = path.split('/').pop()?.replace('.md', '') || '';
        return {
            ...m.metadata,
            slug
        };
    }).sort((a, b) => {
        // Featured posts first
        if (a.featured && !b.featured) return -1;
        if (!a.featured && b.featured) return 1;
        // Then by date
        return new Date(b.date).getTime() - new Date(a.date).getTime();
    });

    return { posts };
};

export const prerender = true;
