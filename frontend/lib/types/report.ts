/**
 * API Types for Report Generation
 * These types match the backend ReportRequest model in app/api/routers/report.py
 */

/**
 * Search agent type for web search
 * - TAVILY: Uses Tavily API for news search
 * - GOOGLE: Uses Google News scraper for news search
 */
export type SearchAgentType = "TAVILY" | "GOOGLE";

/**
 * Request payload for report generation endpoint
 * POST /api/report/generate
 */
export interface ReportRequest {
  /** Company name to generate report for */
  company_name: string;
  /** Start date in DD/MM/YYYY format */
  start_date: string;
  /** End date in DD/MM/YYYY format */
  end_date: string;
  /** Search agent type for web news search */
  agent_type: SearchAgentType;
}
