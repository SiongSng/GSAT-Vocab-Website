<script lang="ts">
    import { State } from "ts-fsrs";

    interface Props {
        state: State;
    }

    let { state }: Props = $props();

    const config = $derived.by(() => {
        switch (state) {
            case State.New:
                return { label: "新", classes: "bg-srs-easy/10 text-srs-easy" };
            case State.Learning:
                return {
                    label: "學習中",
                    classes: "bg-srs-hard/10 text-srs-hard",
                };
            case State.Review:
                return {
                    label: "複習",
                    classes: "bg-srs-good/10 text-srs-good",
                };
            case State.Relearning:
                return {
                    label: "重學",
                    classes: "bg-srs-again/10 text-srs-again",
                };
            default:
                return {
                    label: "未知",
                    classes: "bg-surface-page text-content-tertiary",
                };
        }
    });
</script>

<span class="px-2.5 py-1 text-xs font-medium rounded-full {config.classes}">
    {config.label}
</span>
