<script lang="ts">
    import { getVocabStore } from "$lib/stores/vocab.svelte";
    import { openLookup } from "$lib/stores/word-lookup.svelte";

    interface Props {
        text: string;
        highlightWord?: string;
    }

    let { text, highlightWord }: Props = $props();

    const vocab = getVocabStore();

    const lemmaSet = $derived.by(() => {
        const set = new Set<string>();
        for (const item of vocab.index) {
            set.add(item.lemma.toLowerCase());
        }
        return set;
    });

    const highlightVariants = $derived.by(() => {
        if (!highlightWord) return new Set<string>();
        const lower = highlightWord.toLowerCase();
        const variants = new Set<string>([highlightWord, lower]);

        variants.add(lower + "s");
        variants.add(lower + "es");
        variants.add(lower + "ed");
        variants.add(lower + "ing");
        variants.add(lower + "er");
        variants.add(lower + "est");
        variants.add(lower + "ly");

        if (lower.endsWith("e")) {
            variants.add(lower.slice(0, -1) + "ing");
            variants.add(lower + "d");
        }
        if (lower.endsWith("y")) {
            variants.add(lower.slice(0, -1) + "ies");
            variants.add(lower.slice(0, -1) + "ied");
        }

        return variants;
    });

    interface TextPart {
        text: string;
        isClickable: boolean;
        isHighlighted: boolean;
        lemma: string | null;
    }

    const parts = $derived.by(() => {
        const result: TextPart[] = [];
        const wordRegex = /([a-zA-Z]+(?:'[a-zA-Z]+)?)/g;
        let lastIndex = 0;
        let match: RegExpExecArray | null;

        while ((match = wordRegex.exec(text)) !== null) {
            if (match.index > lastIndex) {
                result.push({
                    text: text.slice(lastIndex, match.index),
                    isClickable: false,
                    isHighlighted: false,
                    lemma: null,
                });
            }

            const word = match[1];
            const lowerWord = word.toLowerCase();
            const isHighlighted = highlightVariants.has(lowerWord);

            let foundLemma: string | null = null;
            if (lemmaSet.size > 0 && !isHighlighted) {
                const baseForms = getBaseForms(lowerWord);
                for (const form of baseForms) {
                    if (lemmaSet.has(form)) {
                        foundLemma = form;
                        break;
                    }
                }
            }

            result.push({
                text: word,
                isClickable: foundLemma !== null,
                isHighlighted,
                lemma: foundLemma,
            });

            lastIndex = match.index + match[0].length;
        }

        if (lastIndex < text.length) {
            result.push({
                text: text.slice(lastIndex),
                isClickable: false,
                isHighlighted: false,
                lemma: null,
            });
        }

        return result;
    });

    function getBaseForms(word: string): string[] {
        const forms = [word];

        if (word.endsWith("s")) {
            forms.push(word.slice(0, -1));
        }
        if (word.endsWith("es")) {
            forms.push(word.slice(0, -2));
        }
        if (word.endsWith("ies")) {
            forms.push(word.slice(0, -3) + "y");
        }
        if (word.endsWith("ed")) {
            forms.push(word.slice(0, -2));
            forms.push(word.slice(0, -1));
            if (word.length > 3 && word[word.length - 3] === word[word.length - 4]) {
                forms.push(word.slice(0, -3));
            }
        }
        if (word.endsWith("ing")) {
            forms.push(word.slice(0, -3));
            forms.push(word.slice(0, -3) + "e");
            if (word.length > 4 && word[word.length - 4] === word[word.length - 5]) {
                forms.push(word.slice(0, -4));
            }
        }
        if (word.endsWith("er")) {
            forms.push(word.slice(0, -2));
            forms.push(word.slice(0, -1));
        }
        if (word.endsWith("est")) {
            forms.push(word.slice(0, -3));
            forms.push(word.slice(0, -2));
        }
        if (word.endsWith("ly")) {
            forms.push(word.slice(0, -2));
        }
        if (word.endsWith("ier")) {
            forms.push(word.slice(0, -3) + "y");
        }
        if (word.endsWith("iest")) {
            forms.push(word.slice(0, -4) + "y");
        }

        return forms;
    }

    function handleClick(lemma: string) {
        openLookup(lemma);
    }
</script>

<span class="clickable-text"
    >{#each parts as part}{#if part.isHighlighted}<mark class="highlight"
                >{part.text}</mark
            >{:else if part.isClickable && part.lemma}<button
                type="button"
                class="clickable-word"
                onclick={() => handleClick(part.lemma!)}
                >{part.text}</button
            >{:else}{part.text}{/if}{/each}</span
>

<style>
    .clickable-text {
        display: inline;
    }

    .clickable-word {
        display: inline;
        padding: 0;
        margin: 0;
        background: none;
        border: none;
        font: inherit;
        color: inherit;
        cursor: pointer;
        border-bottom: 1px dashed var(--color-border-hover);
        transition: all 0.15s ease;
    }

    .clickable-word:hover {
        color: var(--color-accent);
        border-bottom-color: var(--color-accent);
    }

    .highlight {
        background: linear-gradient(
            to top,
            var(--color-highlight) 0%,
            var(--color-highlight) 60%,
            transparent 60%
        );
        padding: 0 2px;
        margin: 0 -2px;
        border-radius: 2px;
        font-weight: 500;
        color: var(--color-content-primary);
    }
</style>
