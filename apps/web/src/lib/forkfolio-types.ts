export type ApiErrorPayload = {
  detail?: string;
  error?: string;
  success?: boolean;
};

export type SearchRecipeResult = {
  id: string | null;
  name: string | null;
  distance: number | null;
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
  success: boolean;
};

export type RecipeEmbeddingRecord = {
  id: string;
  embedding_type: string;
  embedding: number[] | null;
  created_at: string | null;
};

export type RecipeRecord = {
  id: string;
  title: string;
  servings: string | null;
  total_time: string | null;
  source_url: string | null;
  is_test_data: boolean;
  created_at: string | null;
  updated_at: string | null;
  ingredients: string[];
  instructions: string[];
  embeddings?: RecipeEmbeddingRecord[];
};

export type GetRecipeResponse = {
  recipe: RecipeRecord;
  success: boolean;
};

export type ProcessRecipeRequest = {
  raw_input: string;
  enforce_deduplication?: boolean;
  isTest?: boolean;
};

export type ProcessRecipeSuccessResponse = {
  recipe_id: string;
  recipe: RecipeRecord;
  success: true;
  created: boolean;
  message?: string;
};

export type ProcessRecipeFailureResponse = {
  error: string;
  success: false;
};

export type ProcessRecipeResponse =
  | ProcessRecipeSuccessResponse
  | ProcessRecipeFailureResponse;
