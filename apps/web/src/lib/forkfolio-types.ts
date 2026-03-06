export const MIN_RECIPE_INPUT_LENGTH = 10;

export type SearchRecipeResult = {
  id?: string;
  name?: string;
  distance?: number;
  rerank_score?: number;
  embedding_score?: number;
  combined_score?: number;
  raw_rerank_score?: number;
  rerank_mode?: string;
  cuisine_boost?: number;
  family_boost?: number;
};

export type SearchRecipesResponse = {
  query: string;
  count: number;
  results: SearchRecipeResult[];
  success?: boolean;
};

export type RecipeRecord = {
  id: string;
  title: string;
  servings: string | null;
  total_time: string | null;
  source_url: string | null;
  is_test_data?: boolean;
  created_at: string | null;
  updated_at: string | null;
  ingredients: string[];
  instructions: string[];
};

export type GetRecipeResponse = {
  recipe: RecipeRecord;
  success?: boolean;
};

export type ProcessRecipeRequest = {
  raw_input: string;
  enforce_deduplication?: boolean;
  isTest?: boolean;
  is_test?: boolean;
};

export type ProcessRecipeResponse = {
  recipe_id?: string;
  recipe?: RecipeRecord;
  success: boolean;
  created?: boolean;
  message?: string;
  error?: string;
};
