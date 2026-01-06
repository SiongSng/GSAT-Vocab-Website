<script lang="ts">
    import QuizBlank from "$lib/components/quiz/QuizBlank.svelte";
    import { getVocabStore } from "$lib/stores/vocab.svelte";
    import { openLookup } from "$lib/stores/word-lookup.svelte";
    import {
        getAllWordForms,
        getAllPhraseForms,
        getBaseForms,
    } from "$lib/utils/word-forms";
    import {
        generateSpellingHint,
        generatePhraseSpellingHint,
    } from "$lib/utils/spelling";

    interface Props {
        text: string;
        highlightLemma?: string;
        isPhrase?: boolean;
        blankMode?: boolean;
        showHints?: boolean;
    }

    let {
        text,
        highlightLemma,
        isPhrase = false,
        blankMode = false,
        showHints = false,
    }: Props = $props();

    const vocab = getVocabStore();

    interface TextSegment {
        text: string;
        type: "normal" | "highlight" | "clickable";
        lemma?: string;
    }

    function escapeRegex(str: string): string {
        return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    }

    function normalizeWord(word: string): string {
        return word.replace(/'s$/i, "").replace(/n't$/i, "").toLowerCase();
    }

    const segments = $derived.by(() => {
        const result: TextSegment[] = [];
        const currentLemmaSet = vocab.lemmaSet;

        if (!highlightLemma) {
            return processNormalText(text, currentLemmaSet);
        }

        if (isPhrase) {
            const variants = Array.from(getAllPhraseForms(highlightLemma));
            const escapedVariants = variants.map(escapeRegex);
            const pattern = new RegExp(
                `(?<![a-zA-Z])(${escapedVariants.join("|")})(?![a-zA-Z])`,
                "gi",
            );

            let lastIndex = 0;
            let match: RegExpExecArray | null;

            while ((match = pattern.exec(text)) !== null) {
                if (match.index > lastIndex) {
                    const beforeText = text.slice(lastIndex, match.index);
                    result.push(
                        ...processNormalText(beforeText, currentLemmaSet),
                    );
                }
                result.push({ text: match[1], type: "highlight" });
                lastIndex = match.index + match[0].length;
            }

            if (lastIndex < text.length) {
                result.push(
                    ...processNormalText(
                        text.slice(lastIndex),
                        currentLemmaSet,
                    ),
                );
            }
        } else {
            const wordVariants = getAllWordForms(highlightLemma);
            const tokenRegex = /([a-zA-Z]+(?:'[a-zA-Z]+)?)/g;
            let lastIndex = 0;
            let match: RegExpExecArray | null;

            while ((match = tokenRegex.exec(text)) !== null) {
                if (match.index > lastIndex) {
                    result.push({
                        text: text.slice(lastIndex, match.index),
                        type: "normal",
                    });
                }

                const token = match[1];
                const normalized = normalizeWord(token);
                const isHighlighted =
                    wordVariants.has(normalized) ||
                    wordVariants.has(token.toLowerCase());

                if (isHighlighted) {
                    result.push({ text: token, type: "highlight" });
                } else {
                    let foundLemma: string | null = null;
                    if (currentLemmaSet.size > 0) {
                        const baseForms = getBaseForms(normalized);
                        for (const form of baseForms) {
                            if (currentLemmaSet.has(form)) {
                                foundLemma = form;
                                break;
                            }
                        }
                    }
                    if (foundLemma) {
                        result.push({
                            text: token,
                            type: "clickable",
                            lemma: foundLemma,
                        });
                    } else {
                        result.push({ text: token, type: "normal" });
                    }
                }

                lastIndex = match.index + match[0].length;
            }

            if (lastIndex < text.length) {
                result.push({ text: text.slice(lastIndex), type: "normal" });
            }
        }

        return result;
    });

    function processNormalText(
        txt: string,
        lemmaSet: Set<string>,
    ): TextSegment[] {
        const result: TextSegment[] = [];
        const tokenRegex = /([a-zA-Z]+(?:'[a-zA-Z]+)?)/g;
        let lastIndex = 0;
        let match: RegExpExecArray | null;

        while ((match = tokenRegex.exec(txt)) !== null) {
            if (match.index > lastIndex) {
                result.push({
                    text: txt.slice(lastIndex, match.index),
                    type: "normal",
                });
            }

            const token = match[1];
            const normalized = normalizeWord(token);
            let foundLemma: string | null = null;

            if (lemmaSet.size > 0) {
                const baseForms = getBaseForms(normalized);
                for (const form of baseForms) {
                    if (lemmaSet.has(form)) {
                        foundLemma = form;
                        break;
                    }
                }
            }

            if (foundLemma) {
                result.push({
                    text: token,
                    type: "clickable",
                    lemma: foundLemma,
                });
            } else {
                result.push({ text: token, type: "normal" });
            }

            lastIndex = match.index + match[0].length;
        }

        if (lastIndex < txt.length) {
            result.push({ text: txt.slice(lastIndex), type: "normal" });
        }

        return result;
    }

    function handleClick(lemma: string) {
        openLookup(lemma);
    }
</script>

<span class="highlighted-text"
    >{#each segments as seg}{#if seg.type === "highlight"}{#if blankMode}{#if showHints}{#if isPhrase}{@const phraseHint = generatePhraseSpellingHint(seg.text, highlightLemma)}{#each phraseHint.hints as hint, i}{#if i > 0}{" "}{/if}<QuizBlank
                                length={hint.blankLength}
                                prefix={hint.prefix}
                                suffix={hint.suffix}
                                active={true}
                            />{/each}{:else}{@const hint = generateSpellingHint(seg.text, highlightLemma)}<QuizBlank
                                length={hint.blankLength}
                                prefix={hint.prefix}
                                suffix={hint.suffix}
                                active={true}
                            />{/if}{:else}<QuizBlank
                        length={seg.text.length}
                        active={true}
                    />{/if}{:else}<mark class="highlight">{seg.text}</mark
                >{/if}{:else if seg.type === "clickable" && seg.lemma && !blankMode}<button
                type="button"
                class="clickable-word"
                onclick={() => handleClick(seg.lemma!)}>{seg.text}</button
            >{:else}{seg.text}{/if}{/each}</span
>

<style>
    .highlighted-text {
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
