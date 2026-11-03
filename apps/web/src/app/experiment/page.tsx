import ExperimentPageClient, {
  type ExperimentInitialAccess,
} from "@/app/experiment/experiment-page-client";
import { getRequiredViewerUserId } from "@/lib/supabase/viewer";

async function getInitialExperimentAccess(): Promise<ExperimentInitialAccess> {
  const viewerResult = await getRequiredViewerUserId(
    "Experiment threads",
    "Sign in to use experiment threads.",
  );

  if (!viewerResult.viewerUserId) {
    return {
      accessState: viewerResult.status === 503 ? "auth_unavailable" : "auth_required",
      viewerUserId: null,
      errorMessage: null,
    };
  }

  return {
    accessState: "ready",
    viewerUserId: viewerResult.viewerUserId,
    errorMessage: null,
  };
}

export default async function ExperimentPage() {
  const initialAccess = await getInitialExperimentAccess();

  return <ExperimentPageClient initialAccess={initialAccess} />;
}
