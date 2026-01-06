export interface LTResponse {
  matches: LTMatch[];
}

export interface LTMatch {
  message: string;
  shortMessage?: string;
  offset: number;
  length: number;

  context: {
    text: string;
    offset: number;
    length: number;
  };

  replacements: LTReplacement[];

  rule: {
    id: string;
    description: string;
    issueType?: string; // "misspelling", "grammar", etc.
    category?: { id: string; name: string };
  };
}

export interface LTReplacement {
  value: string;
}
