import type { ZodIssue } from "zod";

/**
 * Single typed error surface for every backend interaction.
 * Screens branch on `.code` / `.status` to pick an error state.
 */
export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly issues?: ZodIssue[];

  constructor(opts: {
    code: string;
    message: string;
    status: number;
    issues?: ZodIssue[];
  }) {
    super(opts.message);
    this.name = "ApiError";
    this.code = opts.code;
    this.status = opts.status;
    this.issues = opts.issues;
  }

  /** The known backend integration bug: GET /reports/{id} 500s on hazard-shape mismatch. */
  get isKnownHazardBug(): boolean {
    return (
      this.status === 500 &&
      /hazard|ExtractedSpanField|validation/i.test(this.message)
    );
  }
}
