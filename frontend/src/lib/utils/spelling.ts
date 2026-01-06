import nlp from "compromise";

export interface SpellingHint {
  prefix: string;
  suffix: string;
  blankLength: number;
}

export interface PhraseSpellingHint {
  hints: SpellingHint[];
  words: string[];
}

function detectSuffixUsingNLP(word: string, lemma: string): string {
  const wordLower = word.toLowerCase();
  const lemmaLower = lemma.toLowerCase();

  const doc = nlp(wordLower);

  const asVerb = doc.verbs();
  if (asVerb.found) {
    const infinitive = asVerb.toInfinitive().text().toLowerCase();
    if (infinitive === lemmaLower && wordLower !== lemmaLower) {
      const conj = asVerb.conjugate()[0] as Record<string, string> | undefined;
      if (conj) {
        if (conj["Gerund"]?.toLowerCase() === wordLower) {
          const stem = wordLower.slice(0, -3);
          if (stem.length >= 2) {
            return wordLower.slice(stem.length - 1);
          }
          return "ing";
        }
        if (conj["PastTense"]?.toLowerCase() === wordLower) {
          const stem = wordLower.slice(0, -2);
          if (stem.length >= 2) {
            return wordLower.slice(stem.length - 1);
          }
          return "ed";
        }
        if (conj["PresentTense"]?.toLowerCase() === wordLower) {
          const stem = wordLower.slice(0, -1);
          if (stem.length >= 2) {
            return wordLower.slice(stem.length - 1);
          }
          return "s";
        }
      }
    }
  }

  const asNoun = doc.nouns();
  if (asNoun.found) {
    const singular = asNoun.toSingular().text().toLowerCase();
    if (singular === lemmaLower && wordLower !== lemmaLower) {
      if (wordLower.endsWith("es")) {
        const stem = wordLower.slice(0, -2);
        if (stem.length >= 2) {
          return wordLower.slice(stem.length - 1);
        }
        return "es";
      }
      if (wordLower.endsWith("s")) {
        const stem = wordLower.slice(0, -1);
        if (stem.length >= 2) {
          return wordLower.slice(stem.length - 1);
        }
        return "s";
      }
    }
  }

  const commonSuffixes = [
    { suffix: "tion", minStem: 2 },
    { suffix: "sion", minStem: 2 },
    { suffix: "ment", minStem: 2 },
    { suffix: "ness", minStem: 2 },
    { suffix: "ity", minStem: 2 },
    { suffix: "ful", minStem: 2 },
    { suffix: "less", minStem: 2 },
    { suffix: "ous", minStem: 2 },
    { suffix: "ive", minStem: 2 },
    { suffix: "able", minStem: 2 },
    { suffix: "ible", minStem: 2 },
    { suffix: "ly", minStem: 2 },
  ];

  for (const { suffix, minStem } of commonSuffixes) {
    if (wordLower.endsWith(suffix)) {
      const stem = wordLower.slice(0, -suffix.length);
      if (stem.length >= minStem) {
        return wordLower.slice(stem.length - 1);
      }
    }
  }

  return "";
}

function getRootForm(word: string): string {
  const doc = nlp(word);

  const asVerb = doc.verbs();
  if (asVerb.found) {
    return asVerb.toInfinitive().text();
  }

  const asNoun = doc.nouns();
  if (asNoun.found) {
    return asNoun.toSingular().text();
  }

  const asAdj = doc.adjectives();
  if (asAdj.found) {
    const noun = asAdj.toNoun().text();
    if (noun && noun !== word) {
      return noun;
    }
  }

  return word;
}

function calculatePrefixLength(stemLen: number): number {
  return stemLen <= 4 ? 1 : 2;
}

export function generatePhraseSpellingHint(
  phrase: string,
  lemma?: string,
): PhraseSpellingHint {
  const words = phrase.split(/\s+/);
  const hints = words.map((word) => generateSpellingHint(word, lemma));
  return { hints, words };
}

export function generateSpellingHint(
  word: string,
  lemma?: string,
): SpellingHint {
  const wordLower = word.toLowerCase();
  const len = wordLower.length;

  if (len <= 3) {
    return { prefix: wordLower[0], suffix: "", blankLength: len - 1 };
  }

  const root = lemma ? lemma.toLowerCase() : getRootForm(wordLower);
  const suffix = detectSuffixUsingNLP(wordLower, root);

  if (suffix) {
    const stem = wordLower.slice(0, -suffix.length);
    const stemLen = stem.length;

    if (stemLen <= 3) {
      return { prefix: stem[0], suffix, blankLength: stemLen - 1 };
    }

    const prefixLen = calculatePrefixLength(stemLen);

    return {
      prefix: wordLower.slice(0, prefixLen),
      suffix,
      blankLength: stemLen - prefixLen,
    };
  } else {
    const lastChar = wordLower[len - 1];
    const stemLen = len - 1;

    if (stemLen <= 3) {
      return { prefix: wordLower[0], suffix: lastChar, blankLength: stemLen - 1 };
    }

    const prefixLen = calculatePrefixLength(stemLen);

    return {
      prefix: wordLower.slice(0, prefixLen),
      suffix: lastChar,
      blankLength: stemLen - prefixLen,
    };
  }
}
