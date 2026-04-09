import type { InvestmentReport } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

export async function analyzeTicker(ticker: string): Promise<InvestmentReport> {
  const response = await fetch(`${API_BASE_URL}/analyze/${ticker.toUpperCase()}`, {
    method: "POST",
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Failed to analyze ticker.");
  }

  return (await response.json()) as InvestmentReport;
}

export async function getReport(ticker: string): Promise<InvestmentReport> {
  const response = await fetch(`${API_BASE_URL}/report/${ticker.toUpperCase()}`);

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Failed to fetch report.");
  }

  return (await response.json()) as InvestmentReport;
}
