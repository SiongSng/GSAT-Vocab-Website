import nlp from "compromise";

export function getAllWordForms(word: string): Set<string> {
  const forms = new Set<string>();
  const lower = word.toLowerCase();
  forms.add(lower);

  const doc = nlp(lower);

  const asVerb = doc.verbs();
  if (asVerb.found) {
    const conj = asVerb.conjugate()[0];
    if (conj) {
      Object.values(conj).forEach((form) => {
        if (typeof form === "string") {
          forms.add(form.toLowerCase());
        }
      });
    }
  }

  const asNoun = doc.nouns();
  if (asNoun.found) {
    forms.add(asNoun.toSingular().text().toLowerCase());
    forms.add(asNoun.toPlural().text().toLowerCase());
  }

  const asAdj = doc.adjectives();
  if (asAdj.found) {
    const noun = asAdj.toNoun().text();
    if (noun) forms.add(noun.toLowerCase());

    const adverb = asAdj.toAdverb().text();
    if (adverb) forms.add(adverb.toLowerCase());
  }

  forms.add(lower + "'s");

  return forms;
}

export function getAllPhraseForms(phrase: string): Set<string> {
  const variants = new Set<string>();
  const words = phrase.split(/\s+/);

  if (words.length < 2) {
    return getAllWordForms(phrase);
  }

  const firstWord = words[0];
  const rest = words.slice(1).join(" ");
  const firstWordForms = getAllWordForms(firstWord);

  for (const form of firstWordForms) {
    variants.add(`${form} ${rest}`);
    variants.add(`${form}'s ${rest}`);
  }

  variants.add(phrase);

  return variants;
}

export function getBaseForm(word: string): string {
  const lower = word.toLowerCase();
  const doc = nlp(lower);

  const asVerb = doc.verbs();
  if (asVerb.found) {
    return asVerb.toInfinitive().text().toLowerCase();
  }

  const asNoun = doc.nouns();
  if (asNoun.found) {
    return asNoun.toSingular().text().toLowerCase();
  }

  return lower;
}

export function getBaseForms(word: string): string[] {
  const forms = new Set<string>();
  const normalized = word.replace(/'s$/i, "").replace(/n't$/i, "").toLowerCase();
  forms.add(normalized);

  const baseForm = getBaseForm(normalized);
  forms.add(baseForm);

  return Array.from(forms);
}
