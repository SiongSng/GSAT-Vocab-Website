const API_BASE = "https://gsat-vocab-api.vic0407lu.workers.dev";

export interface QuizQuestion {
  type: string;
  lemma: string;
  prompt: string;
  options?: { label: string; value: string }[];
  correct: string;
  sentence?: string;
}

export async function generateQuiz(params: {
  type: string;
  count: number;
  freqMin?: number;
  freqMax?: number;
  pos?: string[];
  excludePropn?: boolean;
  lemmas?: string[];
  choiceDirection?: string;
}): Promise<QuizQuestion[]> {
  const url = new URL(`${API_BASE}/api/quiz/generate`);
  url.searchParams.set("type", params.type);
  url.searchParams.set("count", String(params.count));
  if (params.freqMin) url.searchParams.set("freq_min", String(params.freqMin));
  if (params.freqMax) url.searchParams.set("freq_max", String(params.freqMax));
  if (params.pos?.length) url.searchParams.set("pos", params.pos.join(","));
  if (params.excludePropn) url.searchParams.set("exclude_propn", "true");
  if (params.lemmas?.length)
    url.searchParams.set("lemmas", params.lemmas.join(","));
  if (params.choiceDirection)
    url.searchParams.set("choice_direction", params.choiceDirection);

  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new Error(`Failed to generate quiz: ${response.status}`);
  }
  const data = await response.json();
  return data.questions || data;
}
