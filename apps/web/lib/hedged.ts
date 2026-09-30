/**
 * Hedged copy enforcement and certainty word list (Constitution 2.IV, FR-038).
 *
 * The interface must never claim autonomous certification, absolute safety, or zero risk.
 */

export const BANNED_CERTAINTY_WORDS: readonly string[] = [
  "certain",
  "certainly",
  "guaranteed",
  "guarantee",
  "safe for flight",
  "cleared for launch",
  "zero risk",
  "defect-free",
  "certified",
  "certification",
  "autonomous certification",
  "100% safe",
  "flawless",
  "risk-free",
];

export const PERMITTED_HEDGES: readonly string[] = [
  "appears",
  "possible",
  "indicated",
  "consistent with",
  "within measured tolerance",
  "observed",
  "suggests",
];

/**
 * Check if text contains any prohibited certainty or certification claims.
 */
export function containsBannedCertaintyClaims(text: string): boolean {
  const lower = text.toLowerCase();
  return BANNED_CERTAINTY_WORDS.some((word) => lower.includes(word.toLowerCase()));
}

/**
 * Validate user-facing copy, throwing in development or logging a warning if certainty words appear.
 */
export function hedged(text: string): string {
  if (containsBannedCertaintyClaims(text)) {
    console.warn(
      `[LaunchGuard Warning] UI string contains banned certainty phrasing (Constitution 2.IV): "${text}"`,
    );
  }
  return text;
}
