export function isExpectedSignedOutMessage(message: string | null | undefined): boolean {
  const normalizedMessage = message?.trim().toLowerCase().replace(/[!.]+$/, "") ?? "";
  return normalizedMessage === "auth session missing";
}
