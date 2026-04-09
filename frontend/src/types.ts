export type AgentOutput = {
  agent: string;
  score: number;
  findings: string[];
  summary: string;
};

export type InvestmentReport = {
  ticker: string;
  conviction_score: number;
  bull_case: string[];
  bear_case: string[];
  risks: string[];
  recommendation: string;
  agent_outputs: Record<string, AgentOutput>;
};
