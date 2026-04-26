export const MIN_RECIPE_INPUT_LENGTH = 10;

export type ApiErrorPayload = {
  detail?: string;
  error?: string;
  message?: string;
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
  success?: boolean;
};

export type RecipeListItem = {
  id: string;
  title: string;
  servings: string | null;
  total_time: string | null;
  source_url: string | null;
  is_public?: boolean;
  created_by_user_id?: string | null;
  is_test_data?: boolean;
  created_at: string | null;
  updated_at: string | null;
};

export type ListRecipesResponse = {
  recipes: RecipeListItem[];
  count: number;
  limit: number;
  cursor: string | null;
  next_cursor: string | null;
  has_more: boolean;
  success?: boolean;
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
  is_public?: boolean;
  created_by_user_id?: string | null;
  is_test_data?: boolean;
  created_at: string | null;
  updated_at: string | null;
  ingredients: string[];
  instructions: string[];
  embeddings?: RecipeEmbeddingRecord[];
};

export type GroceryBagRecipe = Pick<
  RecipeRecord,
  "id" | "title" | "servings" | "total_time"
>;

export type GroceryBagItem = GroceryBagRecipe & {
  added_at: string;
};

export type GetRecipeResponse = {
  recipe: RecipeRecord;
  success?: boolean;
};

export type ProcessRecipeRequest = {
  raw_input: string;
  source_url?: string;
  sourceUrl?: string;
  enforce_deduplication?: boolean;
  is_public?: boolean;
  isPublic?: boolean;
  created_by_user_id?: string;
  createdByUserId?: string;
  isTest?: boolean;
  is_test?: boolean;
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

export type RecipePreviewRecord = {
  title: string;
  ingredients: string[];
  instructions: string[];
  servings: string;
  total_time: string;
};

export type PreviewRecipeFromUrlRequest = {
  url: string;
};

export type PreviewRecipeFromUrlDiagnostics = {
  raw_html_length?: number;
  extracted_text_length?: number;
  cleaned_text_length?: number;
  [key: string]: number | undefined;
};

export type PreviewRecipeFromUrlSuccessResponse = {
  success: true;
  created: false;
  url: string;
  recipe_preview: RecipePreviewRecord;
  diagnostics?: PreviewRecipeFromUrlDiagnostics;
  message?: string;
};

export type PreviewRecipeFromUrlFailureResponse = {
  success: false;
  created: false;
  url: string;
  diagnostics?: PreviewRecipeFromUrlDiagnostics;
  error: string;
};

export type PreviewRecipeFromUrlResponse =
  | PreviewRecipeFromUrlSuccessResponse
  | PreviewRecipeFromUrlFailureResponse;

export type CreateGroceryListRequest = {
  recipe_ids: string[];
};

export type CreateGroceryListResponse = {
  recipe_ids: string[];
  ingredients: string[];
  count: number;
  success?: boolean;
};

export type RecipeBookRecord = {
  id: string;
  name: string;
  normalized_name: string;
  description: string | null;
  created_at: string | null;
  updated_at: string | null;
  recipe_count: number;
  recipe_ids?: string[];
};

export type RecipeBookStats = {
  total_recipe_books: number;
  total_recipe_book_links: number;
  unique_recipes_in_books: number;
  avg_recipes_per_book: number;
};

export type CreateRecipeBookRequest = {
  name: string;
  description?: string | null;
};

export type CreateRecipeBookResponse = {
  recipe_book: RecipeBookRecord;
  created: boolean;
  success?: boolean;
};

export type ListRecipeBooksResponse = {
  recipe_books: RecipeBookRecord[];
  success?: boolean;
};

export type GetRecipeBookResponse = {
  recipe_book: RecipeBookRecord;
  success?: boolean;
};

export type GetRecipeBooksForRecipeResponse = {
  recipe_id: string;
  recipe_books: RecipeBookRecord[];
  success?: boolean;
};

export type GetRecipeBookStatsResponse = {
  stats: RecipeBookStats;
  success?: boolean;
};

export type AddRecipeToBookResponse = {
  recipe_book_id: string;
  recipe_id: string;
  added: boolean;
  success?: boolean;
};

export type RemoveRecipeFromBookResponse = {
  recipe_book_id: string;
  recipe_id: string;
  removed: boolean;
  success?: boolean;
};

export type DeleteRecipeResponse = boolean;

export type ExperimentMessageRole = "system" | "user" | "assistant" | "tool";

export type ExperimentMessageRecord = {
  id: string;
  thread_id: string;
  sequence_no: number;
  role: ExperimentMessageRole;
  content: string;
  tool_name: string | null;
  tool_call: Record<string, unknown> | null;
  created_at: string | null;
};

export type ExperimentThreadRecord = {
  id: string;
  title: string | null;
  metadata: Record<string, unknown>;
  context_recipe_ids: string[];
  messages: ExperimentMessageRecord[];
  created_at: string | null;
  updated_at: string | null;
};

export type CreateExperimentThreadRequest = {
  title?: string;
  context_recipe_ids?: string[];
  is_test?: boolean;
  isTest?: boolean;
};

export type CreateExperimentThreadResponse = {
  thread: ExperimentThreadRecord;
  success?: boolean;
};

export type GetExperimentThreadResponse = {
  thread: ExperimentThreadRecord;
  success?: boolean;
};

export type CreateExperimentMessageRequest = {
  content: string;
  context_recipe_ids?: string[];
  attach_recipe_ids?: string[];
  attach_recipe_names?: string[];
};

export type ExperimentThreadSummary = {
  id: string;
  title: string | null;
  metadata: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
  last_message_role: ExperimentMessageRole | null;
  last_message_content: string | null;
  last_message_created_at: string | null;
};

export type ListExperimentThreadsResponse = {
  threads: ExperimentThreadSummary[];
  count: number;
  success?: boolean;
};

export type CreateExperimentMessageResponse = {
  thread_id: string;
  thread: ExperimentThreadRecord;
  user_message: ExperimentMessageRecord;
  assistant_message: ExperimentMessageRecord;
  attachment_message: ExperimentMessageRecord | null;
  attached_recipes: Array<{
    id: string;
    title: string;
    created_at: string | null;
  }>;
  unresolved_recipe_names: string[];
  success?: boolean;
};
