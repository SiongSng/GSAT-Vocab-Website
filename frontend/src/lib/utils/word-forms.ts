import nlp from "compromise";
import { Inflectors, infinitives } from "en-inflectors";

function findVerbInfinitive(word: string): string | null {
  const lower = word.toLowerCase();
  if (infinitives[lower]) return lower;
  for (const [base, forms] of Object.entries(infinitives)) {
    if (forms.includes(lower)) return base;
  }
  return null;
}

export function getAllWordForms(word: string): Set<string> {
  const forms = new Set<string>();
  const lower = word.toLowerCase();
  forms.add(lower);

  const verbForms = infinitives[lower];
  if (verbForms) {
    verbForms.forEach((form) => forms.add(form));
  } else {
    const inf = new Inflectors(lower);
    forms.add(inf.toPast());
    forms.add(inf.toGerund());
  }

  const doc = nlp(lower);

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

  const infinitive = findVerbInfinitive(lower);
  if (infinitive) return infinitive;

  const doc = nlp(lower);

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
