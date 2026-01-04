<script lang="ts">
    import nlp from "compromise";
    import { getVocabStore } from "$lib/stores/vocab.svelte";
    import { openLookup } from "$lib/stores/word-lookup.svelte";

    interface Props {
        text: string;
        highlightLemma: string;
        isPhrase?: boolean;
    }

    let { text, highlightLemma, isPhrase = false }: Props = $props();

    const vocab = getVocabStore();

    interface TextSegment {
        text: string;
        type: "normal" | "highlight" | "clickable";
        lemma?: string;
    }

    const irregularVerbs: Record<string, string[]> = {
        be: ["am", "is", "are", "was", "were", "been", "being"],
        go: ["goes", "went", "gone", "going"],
        feel: ["feels", "felt", "feeling"],
        take: ["takes", "took", "taken", "taking"],
        make: ["makes", "made", "making"],
        get: ["gets", "got", "gotten", "getting"],
        give: ["gives", "gave", "given", "giving"],
        come: ["comes", "came", "coming"],
        break: ["breaks", "broke", "broken", "breaking"],
        bring: ["brings", "brought", "bringing"],
        keep: ["keeps", "kept", "keeping"],
        put: ["puts", "putting"],
        run: ["runs", "ran", "running"],
        set: ["sets", "setting"],
        spell: ["spells", "spelled", "spelt", "spelling"],
        use: ["uses", "used", "using"],
        try: ["tries", "tried", "trying"],
        let: ["lets", "letting"],
        sit: ["sits", "sat", "sitting"],
        cut: ["cuts", "cutting"],
        hit: ["hits", "hitting"],
        shut: ["shuts", "shutting"],
        begin: ["begins", "began", "begun", "beginning"],
        swim: ["swims", "swam", "swum", "swimming"],
        win: ["wins", "won", "winning"],
        dig: ["digs", "dug", "digging"],
        spin: ["spins", "spun", "spinning"],
        find: ["finds", "found", "finding"],
        hold: ["holds", "held", "holding"],
        stand: ["stands", "stood", "standing"],
        understand: ["understands", "understood", "understanding"],
        leave: ["leaves", "left", "leaving"],
        lose: ["loses", "lost", "losing"],
        meet: ["meets", "met", "meeting"],
        pay: ["pays", "paid", "paying"],
        say: ["says", "said", "saying"],
        sell: ["sells", "sold", "selling"],
        tell: ["tells", "told", "telling"],
        think: ["thinks", "thought", "thinking"],
        buy: ["buys", "bought", "buying"],
        catch: ["catches", "caught", "catching"],
        teach: ["teaches", "taught", "teaching"],
        seek: ["seeks", "sought", "seeking"],
        send: ["sends", "sent", "sending"],
        spend: ["spends", "spent", "spending"],
        build: ["builds", "built", "building"],
        lend: ["lends", "lent", "lending"],
        bend: ["bends", "bent", "bending"],
        sleep: ["sleeps", "slept", "sleeping"],
        sweep: ["sweeps", "swept", "sweeping"],
        weep: ["weeps", "wept", "weeping"],
        creep: ["creeps", "crept", "creeping"],
        leap: ["leaps", "leapt", "leaped", "leaping"],
        deal: ["deals", "dealt", "dealing"],
        dream: ["dreams", "dreamt", "dreamed", "dreaming"],
        learn: ["learns", "learnt", "learned", "learning"],
        mean: ["means", "meant", "meaning"],
        hear: ["hears", "heard", "hearing"],
        read: ["reads", "reading"],
        lead: ["leads", "led", "leading"],
        feed: ["feeds", "fed", "feeding"],
        bleed: ["bleeds", "bled", "bleeding"],
        breed: ["breeds", "bred", "breeding"],
        speed: ["speeds", "sped", "speeding"],
        grow: ["grows", "grew", "grown", "growing"],
        know: ["knows", "knew", "known", "knowing"],
        throw: ["throws", "threw", "thrown", "throwing"],
        show: ["shows", "showed", "shown", "showing"],
        blow: ["blows", "blew", "blown", "blowing"],
        flow: ["flows", "flowed", "flowing"],
        draw: ["draws", "drew", "drawn", "drawing"],
        fly: ["flies", "flew", "flown", "flying"],
        lie: ["lies", "lay", "lain", "lying"],
        lay: ["lays", "laid", "laying"],
        see: ["sees", "saw", "seen", "seeing"],
        eat: ["eats", "ate", "eaten", "eating"],
        beat: ["beats", "beaten", "beating"],
        bite: ["bites", "bit", "bitten", "biting"],
        hide: ["hides", "hid", "hidden", "hiding"],
        ride: ["rides", "rode", "ridden", "riding"],
        write: ["writes", "wrote", "written", "writing"],
        drive: ["drives", "drove", "driven", "driving"],
        rise: ["rises", "rose", "risen", "rising"],
        arise: ["arises", "arose", "arisen", "arising"],
        shine: ["shines", "shone", "shined", "shining"],
        choose: ["chooses", "chose", "chosen", "choosing"],
        freeze: ["freezes", "froze", "frozen", "freezing"],
        speak: ["speaks", "spoke", "spoken", "speaking"],
        steal: ["steals", "stole", "stolen", "stealing"],
        wake: ["wakes", "woke", "woken", "waking"],
        wear: ["wears", "wore", "worn", "wearing"],
        tear: ["tears", "tore", "torn", "tearing"],
        bear: ["bears", "bore", "borne", "born", "bearing"],
        swear: ["swears", "swore", "sworn", "swearing"],
        do: ["does", "did", "done", "doing"],
        have: ["has", "had", "having"],
        sing: ["sings", "sang", "sung", "singing"],
        ring: ["rings", "rang", "rung", "ringing"],
        drink: ["drinks", "drank", "drunk", "drinking"],
        sink: ["sinks", "sank", "sunk", "sinking"],
        shrink: ["shrinks", "shrank", "shrunk", "shrinking"],
        spring: ["springs", "sprang", "sprung", "springing"],
        stink: ["stinks", "stank", "stunk", "stinking"],
    };

    function generateAllVerbForms(word: string): Set<string> {
        const forms = new Set<string>();
        const lower = word.toLowerCase();
        forms.add(lower);

        if (irregularVerbs[lower]) {
            irregularVerbs[lower].forEach((f) => forms.add(f));
        }

        forms.add(lower + "s");
        forms.add(lower + "es");
        forms.add(lower + "ed");
        forms.add(lower + "ing");

        if (lower.endsWith("e")) {
            forms.add(lower.slice(0, -1) + "ing");
            forms.add(lower + "d");
        }

        if (lower.endsWith("y") && lower.length > 1) {
            const beforeY = lower[lower.length - 2];
            if (!"aeiou".includes(beforeY)) {
                forms.add(lower.slice(0, -1) + "ies");
                forms.add(lower.slice(0, -1) + "ied");
            }
        }

        if (lower.length >= 2) {
            const lastChar = lower[lower.length - 1];
            const secondLast = lower[lower.length - 2];
            if (
                "bcdfghlmnprstvwz".includes(lastChar) &&
                "aeiou".includes(secondLast) &&
                (lower.length === 3 || !"aeiou".includes(lower[lower.length - 3]))
            ) {
                forms.add(lower + lastChar + "ing");
                forms.add(lower + lastChar + "ed");
            }
        }

        const doc = nlp(lower);
        const asVerb = doc.verbs();
        if (asVerb.found) {
            const conj = asVerb.conjugate()[0];
            if (conj) {
                Object.values(conj).forEach((form) => {
                    if (typeof form === "string") forms.add(form.toLowerCase());
                });
            }
        }

        return forms;
    }

    function generatePhraseVariants(phrase: string): string[] {
        const variants: string[] = [];
        const words = phrase.split(/\s+/);

        if (words.length < 2) {
            return [phrase];
        }

        const firstWord = words[0];
        const rest = words.slice(1).join(" ");

        const firstWordForms = generateAllVerbForms(firstWord);

        for (const form of firstWordForms) {
            variants.push(`${form} ${rest}`);
            variants.push(`${form}'s ${rest}`);
        }

        variants.push(phrase);

        return [...new Set(variants)];
    }

    function generateWordVariants(word: string): Set<string> {
        const variants = new Set<string>();
        const lower = word.toLowerCase();

        const verbForms = generateAllVerbForms(lower);
        verbForms.forEach((f) => variants.add(f));

        variants.add(lower + "er");
        variants.add(lower + "est");
        variants.add(lower + "ly");
        variants.add(lower + "'s");

        if (lower.endsWith("e")) {
            variants.add(lower.slice(0, -1) + "er");
            variants.add(lower.slice(0, -1) + "est");
        }

        if (lower.endsWith("y") && lower.length > 1) {
            const beforeY = lower[lower.length - 2];
            if (!"aeiou".includes(beforeY)) {
                variants.add(lower.slice(0, -1) + "ier");
                variants.add(lower.slice(0, -1) + "iest");
                variants.add(lower.slice(0, -1) + "ily");
            }
        }

        return variants;
    }

    function escapeRegex(str: string): string {
        return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    }

    function normalizeWord(word: string): string {
        return word.replace(/'s$/i, "").replace(/n't$/i, "").toLowerCase();
    }

    function getBaseForms(word: string): string[] {
        const forms = [word];
        const normalized = normalizeWord(word);
        if (normalized !== word) forms.push(normalized);

        if (word.endsWith("s") && !word.endsWith("ss")) forms.push(word.slice(0, -1));
        if (word.endsWith("es")) forms.push(word.slice(0, -2));
        if (word.endsWith("ies")) forms.push(word.slice(0, -3) + "y");
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
        if (word.endsWith("er") && !word.endsWith("eer")) {
            forms.push(word.slice(0, -2));
            forms.push(word.slice(0, -1));
            forms.push(word.slice(0, -2) + "e");
        }
        if (word.endsWith("est")) {
            forms.push(word.slice(0, -3));
            forms.push(word.slice(0, -2));
            forms.push(word.slice(0, -3) + "e");
        }
        if (word.endsWith("ly")) forms.push(word.slice(0, -2));
        if (word.endsWith("ier")) forms.push(word.slice(0, -3) + "y");
        if (word.endsWith("iest")) forms.push(word.slice(0, -4) + "y");
        if (word.endsWith("ily")) forms.push(word.slice(0, -3) + "y");

        return [...new Set(forms)];
    }

    const segments = $derived.by(() => {
        const result: TextSegment[] = [];
        const currentLemmaSet = vocab.lemmaSet;

        if (isPhrase) {
            const variants = generatePhraseVariants(highlightLemma);
            const escapedVariants = variants.map(escapeRegex);
            const pattern = new RegExp(`(?<![a-zA-Z])(${escapedVariants.join("|")})(?![a-zA-Z])`, "gi");

            let lastIndex = 0;
            let match: RegExpExecArray | null;

            while ((match = pattern.exec(text)) !== null) {
                if (match.index > lastIndex) {
                    const beforeText = text.slice(lastIndex, match.index);
                    result.push(...processNormalText(beforeText, currentLemmaSet));
                }
                result.push({ text: match[1], type: "highlight" });
                lastIndex = match.index + match[0].length;
            }

            if (lastIndex < text.length) {
                result.push(...processNormalText(text.slice(lastIndex), currentLemmaSet));
            }
        } else {
            const wordVariants = generateWordVariants(highlightLemma);
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
                const isHighlighted = wordVariants.has(normalized) || wordVariants.has(token.toLowerCase());

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
                        result.push({ text: token, type: "clickable", lemma: foundLemma });
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

    function processNormalText(txt: string, lemmaSet: Set<string>): TextSegment[] {
        const result: TextSegment[] = [];
        const tokenRegex = /([a-zA-Z]+(?:'[a-zA-Z]+)?)/g;
        let lastIndex = 0;
        let match: RegExpExecArray | null;

        while ((match = tokenRegex.exec(txt)) !== null) {
            if (match.index > lastIndex) {
                result.push({ text: txt.slice(lastIndex, match.index), type: "normal" });
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
                result.push({ text: token, type: "clickable", lemma: foundLemma });
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
    >{#each segments as seg}{#if seg.type === "highlight"}<mark class="highlight"
                >{seg.text}</mark
            >{:else if seg.type === "clickable" && seg.lemma}<button
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
