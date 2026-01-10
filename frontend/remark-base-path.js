import visit from 'unist-util-visit';

const BASE_PATH = process.env.GITHUB_ACTIONS ? '/GSAT-Vocab-Website' : '';

function isInternalPath(url) {
    if (!url) return false;
    if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('//')) return false;
    if (url.startsWith('#') || url.startsWith('mailto:')) return false;
    return url.startsWith('/');
}

export function remarkBasePath() {
    return (tree) => {
        visit(tree, 'link', (node) => {
            if (isInternalPath(node.url)) {
                node.url = BASE_PATH + node.url;
            }
        });

        visit(tree, 'image', (node) => {
            if (isInternalPath(node.url)) {
                node.url = BASE_PATH + node.url;
            }
        });
    };
}
