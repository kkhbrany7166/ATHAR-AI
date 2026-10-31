// Plain-language names for internal identifiers. Codes stay available in tooltips and details.

export const CRITERION_SHORT: Record<string, string> = {
  C1: "Typical inputs",
  C2: "Smallest input",
  C3: "Explains why it stops",
  C4: "Explains how results combine",
};

export const MISCONCEPTION_SHORT: Record<string, string> = {
  "MC-BASE-SMALLEST": "Stops after the smallest input",
  "MC-BASE-VALUE": "Wrong base-case value",
  "MC-STOP-IMPLICIT": "Thinks recursion stops by itself",
  "MC-NO-PROGRESS": "Recursive call doesn't shrink",
};

export const OBJECTIVE_SHORT: Record<string, string> = {
  "REC-1": "Base cases",
  "REC-2": "Progress toward the base case",
  "REC-3": "How results combine",
};

export const criterionLabel = (code: string) => CRITERION_SHORT[code] ?? code;
export const misconceptionLabel = (code: string) => MISCONCEPTION_SHORT[code] ?? code;
export const objectiveLabel = (code: string) => OBJECTIVE_SHORT[code] ?? code;
