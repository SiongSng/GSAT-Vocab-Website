const BASE_TITLE = "學測英文高頻單字";
const BASE_URL = "https://siongsng.github.io/GSAT-Vocab-Website";

interface SEOConfig {
  title: string;
  description?: string;
  canonical?: string;
}

interface WordStructuredData {
  lemma: string;
  pos: string[];
  definitions: string[];
  examples: string[];
}

const routeTitles: Record<string, SEOConfig> = {
  browse: {
    title: BASE_TITLE,
    description:
      "從歷屆學測試題萃取 5000+ 高頻單字，提供智慧複習、詞頻統計與字根拆解功能。",
    canonical: BASE_URL + "/",
  },
  flashcard: {
    title: `單字卡複習 | ${BASE_TITLE}`,
    description:
      "間隔記憶演算法智慧安排複習時程，依遺忘曲線科學化背單字，學習效率倍增。",
    canonical: BASE_URL + "/flashcard",
  },
  "flashcard-session": {
    title: `複習中 | ${BASE_TITLE}`,
    canonical: BASE_URL + "/flashcard/session",
  },
  quiz: {
    title: `測驗模式 | ${BASE_TITLE}`,
    description:
      "多元題型測驗單字掌握程度，即時回饋學習成效，精準找出需加強的弱點單字。",
    canonical: BASE_URL + "/quiz",
  },
  "quiz-session": {
    title: `測驗中 | ${BASE_TITLE}`,
    canonical: BASE_URL + "/quiz/session",
  },
};

export function updatePageSEO(routeName: string, wordLemma?: string): void {
  let config: SEOConfig;

  if (routeName === "word" && wordLemma) {
    config = {
      title: `${wordLemma} 的意思 | ${BASE_TITLE}`,
      description: `「${wordLemma}」完整釋義、例句、字根分析與相關詞彙，學測高頻單字資料庫。`,
      canonical: `${BASE_URL}/word/${encodeURIComponent(wordLemma)}`,
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

  if (config.canonical) {
    updateCanonicalURL(config.canonical);
  }

  updateOGURL(config.canonical || BASE_URL);

  updateBreadcrumbForRoute(routeName, wordLemma);
}

function updateMetaTag(selector: string, attr: string, value: string): void {
  const el = document.querySelector(selector);
  if (el) el.setAttribute(attr, value);
}

function updateCanonicalURL(url: string): void {
  let link = document.querySelector('link[rel="canonical"]');
  if (!link) {
    link = document.createElement("link");
    link.setAttribute("rel", "canonical");
    document.head.appendChild(link);
  }
  link.setAttribute("href", url);
}

function updateOGURL(url: string): void {
  updateMetaTag('meta[property="og:url"]', "content", url);
}

export function updateBreadcrumbForRoute(
  routeName: string,
  wordLemma?: string,
): void {
  const items: Array<{ name: string; url: string }> = [
    { name: "首頁", url: BASE_URL + "/" },
  ];

  switch (routeName) {
    case "browse":
      break;
    case "word":
      if (wordLemma) {
        items.push({
          name: wordLemma,
          url: `${BASE_URL}/word/${encodeURIComponent(wordLemma)}`,
        });
      }
      break;
    case "flashcard":
      items.push({ name: "單字卡複習", url: BASE_URL + "/flashcard" });
      break;
    case "flashcard-session":
      items.push({ name: "單字卡複習", url: BASE_URL + "/flashcard" });
      items.push({ name: "複習中", url: BASE_URL + "/flashcard/session" });
      break;
    case "quiz":
      items.push({ name: "測驗模式", url: BASE_URL + "/quiz" });
      break;
    case "quiz-session":
      items.push({ name: "測驗模式", url: BASE_URL + "/quiz" });
      items.push({ name: "測驗中", url: BASE_URL + "/quiz/session" });
      break;
  }

  updateBreadcrumb(items);
}

export function updateBreadcrumb(
  items: Array<{ name: string; url: string }>,
): void {
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
        item: item.url,
      })),
    };
    breadcrumbScript.textContent = JSON.stringify(breadcrumb);
  }
}

export function updateWordStructuredData(
  data: WordStructuredData | null,
): void {
  const existingScript = Array.from(
    document.querySelectorAll('script[type="application/ld+json"]'),
  ).find((s) => s.textContent?.includes('"@type":"DefinedTerm"'));

  if (existingScript) {
    existingScript.remove();
  }

  if (!data) return;

  const script = document.createElement("script");
  script.type = "application/ld+json";

  const structuredData = {
    "@context": "https://schema.org",
    "@type": "DefinedTerm",
    "@id": `${BASE_URL}/word/${encodeURIComponent(data.lemma)}`,
    name: data.lemma,
    description: data.definitions.join("; "),
    inDefinedTermSet: {
      "@type": "DefinedTermSet",
      name: "學測高頻單字資料庫",
      url: BASE_URL,
    },
    termCode: data.pos.join(", "),
    ...(data.examples.length > 0 && {
      example: data.examples.slice(0, 3).map((ex) => ({
        "@type": "CreativeWork",
        text: ex,
      })),
    }),
  };

  script.textContent = JSON.stringify(structuredData);
  document.head.appendChild(script);
}
