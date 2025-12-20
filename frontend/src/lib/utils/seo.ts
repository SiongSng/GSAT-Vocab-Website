const BASE_TITLE = "學測高頻單字";
const TITLE_SUFFIX = " | 數據分析 · 科學備考";

interface SEOConfig {
  title: string;
  description?: string;
}

const routeTitles: Record<string, SEOConfig> = {
  browse: {
    title: BASE_TITLE + TITLE_SUFFIX,
    description:
      "從歷屆學測試題萃取 5000+ 高頻單字，智慧複習排程搭配詞頻統計與字根拆解，備考效率大提升。",
  },
  flashcard: {
    title: `單字卡複習 | ${BASE_TITLE}`,
    description:
      "間隔記憶演算法智慧安排複習時程，依遺忘曲線科學化背單字，學習效率倍增。",
  },
  "flashcard-session": {
    title: `複習中 | ${BASE_TITLE}`,
  },
  quiz: {
    title: `測驗模式 | ${BASE_TITLE}`,
    description:
      "多元題型測驗單字掌握程度，即時回饋學習成效，精準找出需加強的弱點單字。",
  },
  "quiz-session": {
    title: `測驗中 | ${BASE_TITLE}`,
  },
  stats: {
    title: `學習統計 | ${BASE_TITLE}`,
    description:
      "視覺化學習進度與統計分析，追蹤每日複習量、記憶保持率、單字掌握度一目瞭然。",
  },
};

export function updatePageSEO(routeName: string, wordLemma?: string): void {
  let config: SEOConfig;

  if (routeName === "word" && wordLemma) {
    config = {
      title: `${wordLemma} 的意思 | ${BASE_TITLE}`,
      description: `「${wordLemma}」完整釋義、例句、字根分析與相關詞彙，學測高頻單字資料庫。`,
    };
  } else {
    config = routeTitles[routeName] || routeTitles.browse;
  }

  document.title = config.title;

  if (config.description) {
    updateMetaTag('meta[name="description"]', "content", config.description);
    updateMetaTag(
      'meta[property="og:description"]',
      "content",
      config.description,
    );
    updateMetaTag(
      'meta[name="twitter:description"]',
      "content",
      config.description,
    );
  }

  updateMetaTag('meta[name="title"]', "content", config.title);
  updateMetaTag('meta[property="og:title"]', "content", config.title);
  updateMetaTag('meta[name="twitter:title"]', "content", config.title);
}

function updateMetaTag(selector: string, attr: string, value: string): void {
  const el = document.querySelector(selector);
  if (el) el.setAttribute(attr, value);
}

export function updateBreadcrumb(
  items: Array<{ name: string; url?: string }>,
): void {
  const script = document.querySelector('script[type="application/ld+json"]');
  if (!script) return;

  const breadcrumbScript = Array.from(
    document.querySelectorAll('script[type="application/ld+json"]'),
  ).find((s) => s.textContent?.includes("BreadcrumbList"));

  if (breadcrumbScript) {
    const breadcrumb = {
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      itemListElement: items.map((item, index) => ({
        "@type": "ListItem",
        position: index + 1,
        name: item.name,
        ...(item.url && { item: item.url }),
      })),
    };
    breadcrumbScript.textContent = JSON.stringify(breadcrumb);
  }
}
