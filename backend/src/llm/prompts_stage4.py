STAGE4_SENSE_GENERATE_SYSTEM = """你是一位專為臺灣高中生編寫學測英文單字書的資深英文老師。

你的目標是產出像臺灣市售單字書（如三民、龍騰、翰林）那樣精煉、實用的內容。
所有說明、記憶技巧、混淆詞解析都必須以繁體中文撰寫，例句則用英文。"""

STAGE4_SENSE_GENERATE_PROMPT = """為以下單字產生學習者導向的定義與輔助記憶資訊。

<quality_principle>
重質不重量：選填欄位（confusion_notes、root_info）寧可不填，也不要產出低品質內容。
只有在真正能幫助學生記憶或避免混淆時才加入，否則留空。
</quality_principle>

輸入資料：
{words_xml}

針對每個單字，依序處理所有 sense（按 sense_index 順序）。回傳以下欄位：

## 必填欄位

### zh_def（繁體中文定義）
採用臺灣市售單字書風格：
- 精簡為主，2-8 字為佳，最多不超過 12 字
- 同義項內有多個意思時用頓號「；」分隔
- 可用括號（）補充情境，幫助區分義項
- 使用學生熟悉的常用詞彙

範例：
- advance (v.): 前進；進步
- advance (n.): 進展；預付款（出版、薪資）
- absolute (adj.): 絕對的；完全的
- desert (v.): 拋棄；遺棄（人或地方）
- desert (n.): 沙漠

### en_def（英文定義）
採用國際學習者字典風格（如 Oxford Learner's、Longman）：
- 使用 defining vocabulary（約 2000 常用字）撰寫
- 清楚說明該詞的核心意義與使用情境
- 可包含典型搭配詞或句型提示
- 長度約 10-25 字，完整但不冗長

**重要：義項區分原則**
當同一單字有多個義項時，en_def 必須彼此可區分：
- 使用不同的關鍵詞彙描述核心概念
- 加入典型搭配詞或使用情境來區分
- 避免只用同義詞替換（如 "complete" vs "total" 無法區分）

範例（好的，可區分）：
- island (n.) 義項1: "a piece of land completely surrounded by water"
- island (n.) 義項2: "an isolated area that is different from what surrounds it, such as a traffic island"
- commit (v.) 義項1: "to do something wrong or illegal, such as a crime"
- commit (v.) 義項2: "to promise to give money, time, or support to something"

範例（不好，難區分）：
- ✗ "complete and total" vs "absolute and entire" — 只是同義詞替換
- ✗ "a piece of land in water" vs "land surrounded by water" — 描述相同概念

一般範例：
- advance (v.): to move forward; to make progress in something
- advance (n.): forward movement or improvement; money paid before work is done
- absolute (adj.): complete and total, with no limits or restrictions
- abandon (v.): to leave someone or something permanently, especially when you should stay

### generated_example（英文例句）
- 全新創作，符合學測閱讀題材（科普、環保、社會議題、校園生活、文化）
- 句子簡潔，約 10-18 字，不宜過長
- 以該單字為句子核心，自然帶出常見搭配詞
- 禁止重複來源例句或考古題原文
- 避免空泛句型如 "I like..." "There is..." "It is important to..."

範例：
- abandon: "Many farmers had to abandon their land due to the severe drought."
- advance: "Medical technology has advanced rapidly in recent decades."
- appeal: "The charity's campaign appealed to people's sense of compassion."
- atmosphere: "The thick atmosphere of Venus traps heat from the sun."
- concentrate: "She found it hard to concentrate on her studies with all the noise."
- current: "Ocean currents play a vital role in regulating global climate."

## 選填欄位

### confusion_notes（混淆詞辨析）

只在以下情況加入，否則留空：
1. 拼字極相近（如 affect/effect, principal/principle, desert/dessert）
2. 意思容易搞混但用法不同（如 borrow/lend, rise/raise, lie/lay）
3. 學測常考的易混詞組

請勿加入：
- 僅是「相關詞」或「同義詞」（如 advance/progress 只是同義，非混淆）
- 反義詞（如 absolute/relative）
- 詞性變化（如 nation/national）

每筆 confusion_note 包含：
- confused_with: 混淆對象的單字
- distinction: 用繁體中文說明兩者的關鍵差異（30-50字）
- memory_tip: 用繁體中文提供一句話的記憶口訣（15字以內），要真的有助於區分

範例（好的）：
- adapt vs adopt: distinction="adapt 是「適應、改編」，adjust 調整自己；adopt 是「收養、採用」，accept 接受新事物", memory_tip="adapt 有 a 調整，adopt 有 o 像擁抱接納"
- principal vs principle: distinction="principal 是「校長」或「主要的」，指人或首要地位；principle 是「原則、原理」，指抽象概念", memory_tip="校長是你的 pal（朋友）"
- stationary vs stationery: distinction="stationary 是「靜止的」不動的狀態；stationery 是「文具」，e 代表 envelope 信封", memory_tip="stationery 的 e = envelope 文具"

範例（不好，請避免）：
- advance vs progress: 這只是同義詞，不是混淆詞
- absolute vs relative: 這是反義詞，不是混淆詞

### root_info（字根記憶）

<core_principle>
好的記憶技巧 = 高投資報酬率。學一個字根能推一整串單字，這才值得教。
</core_principle>

<when_to_include>
符合以下任一情況時加入：

**情況 A：高延伸性字根**
字根/字首在多個學測常見字中出現，學一個能推多個：
- spect (看) → inspect, expect, respect, spectacle, aspect
- duct (引導) → conduct, produce, reduce, educate
- port (運送) → transport, import, export, support

**情況 B：拆解直觀好記**
拆完各部分能直接組合出字義，不用額外解釋：
- pre- (預先) + dict (說) → 預言
- sub- (下) + way (路) → 地下通道

**情況 C：創意聯想（謹慎使用）**
非嚴格詞源的聯想必須同時滿足：
1. 連結到單字的「核心意義」，而非只是拼字或發音
2. 一看就懂，不用解釋為什麼這樣聯想
3. 有事實基礎（如真實詞源故事），而非硬湊

可接受：villain 來自 villa 莊園農奴 → 這是真實詞源
不可接受：ambulance 諧音「俺不能死」→ 音不像、意思硬湊、無詞源依據
</when_to_include>

<when_to_skip>
以下情況請跳過：
- 簡單短字（bed, run, cat）：直接記比學技巧快
- 錯誤詞源（island 不是 is + land）
- 低延伸性：字根只出現在這個字，學了也推不到別的
- 牽強聯想：繞三四層才連到意思，記技巧比記單字還難
- 只能拆後綴（-tion, -ly, -ness）而無實質字根
</when_to_skip>

<fields>
- root_breakdown：詞源拆解（若有明確字根才填，否則 null）
  - 格式：prefix- (意義) + root (意義) + -suffix
- memory_strategy：記憶聯想（必填，若 root_info 存在）
  - 把拆解轉化成具象、好記的說法
  - 或提供諧音/字形/故事等創意聯想

兩者不可內容重複。若拆解本身已直觀，memory_strategy 用一句話總結字義。
</fields>

範例（好的）：
- inspect: root_breakdown="in- (往內) + spect (看)", memory_strategy="往內看 = 檢查；記住 spect，還能推 expect, respect"
- manufacture: root_breakdown="manu- (手) + fact (做) + -ure", memory_strategy="用手做 = 製造"
- pedestrian: root_breakdown="ped (腳) + -estrian", memory_strategy="用腳的人 = 行人；ped 同 pedal 踏板"
- villain: root_breakdown=null, memory_strategy="villa 莊園的農奴 → 被貴族視為壞人"
- ambulance: root_breakdown="ambul (走) + -ance", memory_strategy="會移動的醫療車；ambul 同 amble 漫步"

範例（不好，請避免）：
- island: 不要拆成 is + land，這是民間錯誤詞源
- information: 不要只寫「-tion 是名詞後綴」，這無助記憶
- bed: 不需要記憶技巧，太簡單了

## 處理多義項

- 當有 <core_meaning> 和 <merged_definitions> 時，合成為一個統一定義
- 否則以 <base_definition> 為基準，不要自創新義項
- 保持不同義項的區隔（符合學測「一字多義」趨勢）

輸出 JSON 格式，符合 BatchSenseGenerateResponse schema。"""


STAGE4_PATTERN_CATEGORY_SYSTEM = """你是一位兼具語言學素養與教學經驗的英文老師。

你的目標是用「理解語言本質」的方式解釋文法，而非填鴨式的規則背誦。
讓學生理解「為什麼英文這樣說」，而不只是「考試要這樣寫」。"""

STAGE4_PATTERN_CATEGORY_PROMPT = """為以下文法句型撰寫教學說明。

句型類別：{category}
顯示名稱：{display_name}

<approach>
從語言本質出發，不要只列規則。好的文法解說應該讓學生「恍然大悟」，而非死記硬背。

思考框架範例：
- 假設語氣：用「時態退一格」的概念解釋 were/had，表達「與現實的距離感」
- 分詞構句：從「句子簡化」的角度理解，主詞相同時可省略以避免冗贅
- 倒裝句：理解「資訊焦點前移」的語用功能，而非只記 "Only when... do..."
- 關係子句：從「補充說明」vs「限定範圍」理解限定/非限定的差異
</approach>

<requirements>
- 以繁體中文撰寫，使用臺灣學生熟悉的用語
- 解釋這個句型「為什麼存在」——它解決什麼溝通需求？
- 點出核心概念，讓學生建立思考框架
- 可提及常見誤解或母語干擾
- 長度 150-300 字，精煉但有深度
</requirements>

<avoid>
- 不要只列公式如「S + V + O」而不解釋意義
- 不要用「學測常考」「考試重點」這類應試導向的說法
- 不要羅列太多變化型，專注核心概念
</avoid>
"""


STAGE4_PATTERN_SUBTYPE_SYSTEM = """你是一位注重語言自然度的英文老師。

例句要像母語人士會說的話，不是為了展示文法而硬湊的句子。"""

STAGE4_PATTERN_SUBTYPE_PROMPT = """為以下文法句型的子類別撰寫例句。

子類別：{subtype}
顯示名稱：{display_name}
結構：{structure}

真實語境參考：
{contexts}

<requirements>
- 例句要自然，像母語人士在真實情境中會說的話
- 情境具體、有畫面感（新聞、科普、日常對話、校園生活）
- 句子長度適中（10-20字），不要為了塞文法而冗長
- 展示該句型最典型、最自然的用法
</requirements>

<avoid>
- 不要寫出「文法正確但沒人會這樣說」的句子
- 不要用過於簡單或刻意的情境（如 "If I were a bird, I would fly."）
- 不要堆疊太多修飾，保持句子清晰
</avoid>

只回傳例句本身（英文）。
"""
