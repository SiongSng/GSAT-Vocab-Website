type RouteType =
  | { name: "browse"; params?: undefined }
  | { name: "word"; params: { lemma: string; senseId?: string } }
  | { name: "flashcard"; params?: undefined }
  | { name: "flashcard-session"; params?: undefined }
  | { name: "quiz"; params?: undefined }
  | { name: "quiz-session"; params?: undefined }
  | { name: "stats"; params?: undefined };

interface RouterStore {
  route: RouteType;
  isNavigating: boolean;
}

const store: RouterStore = $state({
  route: { name: "browse" },
  isNavigating: false,
});

function getBasePath(): string {
  const base = import.meta.env.BASE_URL || "/";
  return base.endsWith("/") ? base.slice(0, -1) : base;
}

const ROUTE_PATTERNS: Array<{
  pattern: RegExp;
  parse: (match: RegExpMatchArray) => RouteType;
}> = [
  {
    pattern: /^\/word\/([^/]+)\/([^/]+)$/,
    parse: (m) => ({
      name: "word",
      params: { lemma: decodeURIComponent(m[1]), senseId: decodeURIComponent(m[2]) },
    }),
  },
  {
    pattern: /^\/word\/([^/]+)$/,
    parse: (m) => ({ name: "word", params: { lemma: decodeURIComponent(m[1]) } }),
  },
  {
    pattern: /^\/flashcard\/session$/,
    parse: () => ({ name: "flashcard-session" }),
  },
  {
    pattern: /^\/flashcard$/,
    parse: () => ({ name: "flashcard" }),
  },
  {
    pattern: /^\/quiz\/session$/,
    parse: () => ({ name: "quiz-session" }),
  },
  {
    pattern: /^\/quiz$/,
    parse: () => ({ name: "quiz" }),
  },
  {
    pattern: /^\/stats$/,
    parse: () => ({ name: "stats" }),
  },
  {
    pattern: /^\/$/,
    parse: () => ({ name: "browse" }),
  },
];

function parseRoute(fullPath: string): RouteType {
  const basePath = getBasePath();
  let path = fullPath;
  if (basePath && path.startsWith(basePath)) {
    path = path.slice(basePath.length) || "/";
  }
  const normalizedPath = path || "/";
  for (const { pattern, parse } of ROUTE_PATTERNS) {
    const match = normalizedPath.match(pattern);
    if (match) {
      return parse(match);
    }
  }
  return { name: "browse" };
}

function routeToPath(route: RouteType): string {
  const basePath = getBasePath();
  let path: string;
  switch (route.name) {
    case "browse":
      path = "/";
      break;
    case "word":
      path = route.params.senseId
        ? `/word/${encodeURIComponent(route.params.lemma)}/${encodeURIComponent(route.params.senseId)}`
        : `/word/${encodeURIComponent(route.params.lemma)}`;
      break;
    case "flashcard":
      path = "/flashcard";
      break;
    case "flashcard-session":
      path = "/flashcard/session";
      break;
    case "quiz":
      path = "/quiz";
      break;
    case "quiz-session":
      path = "/quiz/session";
      break;
    case "stats":
      path = "/stats";
      break;
  }
  return basePath + path;
}

export function getRouterStore() {
  return {
    get route() {
      return store.route;
    },
    get isNavigating() {
      return store.isNavigating;
    },
  };
}

export function initRouter(): void {
  store.route = parseRoute(window.location.pathname);
  window.addEventListener("popstate", handlePopState);
}

export function destroyRouter(): void {
  window.removeEventListener("popstate", handlePopState);
}

function handlePopState(): void {
  store.route = parseRoute(window.location.pathname);
}

export function navigate(route: RouteType, options?: { replace?: boolean }): void {
  const path = routeToPath(route);
  if (options?.replace) {
    window.history.replaceState(null, "", path);
  } else {
    window.history.pushState(null, "", path);
  }
  store.route = route;
}

export function navigateTo(path: string, options?: { replace?: boolean }): void {
  const route = parseRoute(path);
  navigate(route, options);
}

export function back(): void {
  window.history.back();
}

export function forward(): void {
  window.history.forward();
}
