from ..models.exam import PatternCategory, PatternSubtype


def get_category_display_name(category: PatternCategory) -> str:
    """Get Chinese display name for pattern category."""
    mapping = {
        PatternCategory.SUBJUNCTIVE: "假設語氣",
        PatternCategory.INVERSION: "倒裝句",
        PatternCategory.PARTICIPLE: "分詞構句",
        PatternCategory.CLEFT_SENTENCE: "分裂句",
        PatternCategory.COMPARISON_ADV: "比較句型",
        PatternCategory.CONCESSION_ADV: "讓步句型",
        PatternCategory.RESULT_PURPOSE: "結果與目的句型",
    }
    return mapping.get(category, category.value)


def get_subtype_display_name(subtype: PatternSubtype) -> str:
    """Get Chinese display name for pattern subtype."""
    mapping = {
        PatternSubtype.SUBJ_WISH_PAST: "wish + 過去式（與現在事實相反）",
        PatternSubtype.SUBJ_WISH_PAST_PERFECT: "wish + 過去完成式（與過去事實相反）",
        PatternSubtype.SUBJ_AS_IF: "as if / as though（彷彿）",
        PatternSubtype.SUBJ_WERE_TO: "If...were to...（假設未來）",
        PatternSubtype.SUBJ_SHOULD: "should 假設語氣",
        PatternSubtype.SUBJ_HAD: "had 假設語氣",
        PatternSubtype.SUBJ_DEMAND: "demand/suggest 要求建議動詞",
        PatternSubtype.SUBJ_IF_ONLY: "if only（要是...就好了）",
        PatternSubtype.SUBJ_BUT_FOR: "but for / without（要不是）",
        PatternSubtype.SUBJ_ITS_TIME: "It's time (that)...（該是...的時候了）",
        PatternSubtype.INV_NEGATIVE: "否定副詞倒裝",
        PatternSubtype.INV_NOT_ONLY: "not only...but also 倒裝",
        PatternSubtype.INV_NO_SOONER: "no sooner...than 倒裝",
        PatternSubtype.INV_ONLY: "only 開頭倒裝",
        PatternSubtype.INV_SO_ADJ: "so + adj/adv + that 倒裝",
        PatternSubtype.INV_CONDITIONAL: "條件句倒裝（省略 if）",
        PatternSubtype.INV_NOT_UNTIL: "not until 倒裝",
        PatternSubtype.PART_PERFECT: "完成式分詞（Having + p.p.）",
        PatternSubtype.PART_WITH: "with + 名詞 + 分詞",
        PatternSubtype.PART_ABSOLUTE: "獨立分詞構句",
        PatternSubtype.CLEFT_IT_THAT: "It is/was...that 強調句",
        PatternSubtype.CLEFT_WHAT: "What...is/was 名詞子句強調",
        PatternSubtype.COMP_THE_MORE: "the more...the more",
        PatternSubtype.COMP_NO_MORE_THAN: "no more...than（一樣不...）",
        PatternSubtype.COMP_TIMES: "倍數 + as...as",
        PatternSubtype.CONC_NO_MATTER: "no matter + wh-",
        PatternSubtype.CONC_WHATEVER: "whatever / however 讓步",
        PatternSubtype.CONC_ADJ_AS: "adj + as + 主詞 + 動詞",
        PatternSubtype.RES_SO_THAT: "so...that（結果）",
        PatternSubtype.RES_SUCH_THAT: "such...that（結果）",
        PatternSubtype.PURP_LEST: "lest（以免）",
        PatternSubtype.PURP_FOR_FEAR: "for fear that（唯恐）",
    }
    return mapping.get(subtype, subtype.value)


def get_subtype_structure(subtype: PatternSubtype) -> str:
    """Get English structure pattern for pattern subtype."""
    mapping = {
        PatternSubtype.SUBJ_WISH_PAST: "I wish + S + Ved/were",
        PatternSubtype.SUBJ_WISH_PAST_PERFECT: "I wish + S + had + p.p.",
        PatternSubtype.SUBJ_AS_IF: "S + V + as if/though + S + Ved/were",
        PatternSubtype.SUBJ_WERE_TO: "If + S + were to + V..., S + would/could + V",
        PatternSubtype.SUBJ_SHOULD: "If + S + should + V..., S + will/would + V",
        PatternSubtype.SUBJ_HAD: "If + S + had + p.p., S + would have + p.p.",
        PatternSubtype.SUBJ_DEMAND: "S + demand/suggest + that + S + (should) + V",
        PatternSubtype.SUBJ_IF_ONLY: "If only + S + Ved/were/had p.p.",
        PatternSubtype.SUBJ_BUT_FOR: "But for/Without + N, S + would + V",
        PatternSubtype.SUBJ_ITS_TIME: "It's time (that) + S + Ved",
        PatternSubtype.INV_NEGATIVE: "Negative adverb + Aux + S + V",
        PatternSubtype.INV_NOT_ONLY: "Not only + Aux + S + V..., but (S) also...",
        PatternSubtype.INV_NO_SOONER: "No sooner + had + S + p.p. + than + S + Ved",
        PatternSubtype.INV_ONLY: "Only + adverbial + Aux + S + V",
        PatternSubtype.INV_SO_ADJ: "So + adj/adv + Aux + S + V + that...",
        PatternSubtype.INV_CONDITIONAL: "Had/Were/Should + S + ..., S + would + V",
        PatternSubtype.INV_NOT_UNTIL: "Not until + clause/time + Aux + S + V",
        PatternSubtype.PART_PERFECT: "Having + p.p., S + V",
        PatternSubtype.PART_WITH: "With + N + Ving/p.p., S + V",
        PatternSubtype.PART_ABSOLUTE: "N + Ving/p.p., S + V",
        PatternSubtype.CLEFT_IT_THAT: "It is/was + N/phrase + that + S + V",
        PatternSubtype.CLEFT_WHAT: "What + S + V + is/was + N/phrase",
        PatternSubtype.COMP_THE_MORE: "The + comparative..., the + comparative",
        PatternSubtype.COMP_NO_MORE_THAN: "S + be + no more + adj + than + S",
        PatternSubtype.COMP_TIMES: "N times + as + adj + as",
        PatternSubtype.CONC_NO_MATTER: "No matter + wh- + S + V, S + V",
        PatternSubtype.CONC_WHATEVER: "Whatever/However + adj/adv + S + V, S + V",
        PatternSubtype.CONC_ADJ_AS: "Adj/Adv + as + S + V, S + V",
        PatternSubtype.RES_SO_THAT: "S + V + so + adj/adv + that + S + V",
        PatternSubtype.RES_SUCH_THAT: "S + V + such + (a/an) + adj + N + that + S + V",
        PatternSubtype.PURP_LEST: "S + V + lest + S + (should) + V",
        PatternSubtype.PURP_FOR_FEAR: "S + V + for fear that + S + might/should + V",
    }
    return mapping.get(subtype, "")
