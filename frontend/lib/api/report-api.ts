/**
 * Report API Service
 * Handles communication with the backend report generation endpoint
 */

import { format } from "date-fns";
import { ReportRequest, SearchAgentType } from "../types/report";

import { apiFetch } from "./access";

/**
 * Formats a Date object to DD/MM/YYYY string format
 * @param date - Date object to format
 * @returns Formatted date string in DD/MM/YYYY format
 */
export function formatDateForAPI(date: Date): string {
  return format(date, "dd/MM/yyyy");
}

/**
 * Error class for API errors with status code
 */
export class ReportAPIError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public details?: string
  ) {
    super(message);
    this.name = "ReportAPIError";
  }
}

/**
 * Generates a company report by calling the backend API
 * @param companyName - Name of the company
 * @param startDate - Start date for the report period
 * @param endDate - End date for the report period
 * @param agentType - Search agent type (TAVILY or GOOGLE)
 * @returns Promise<Blob> - PDF file as a Blob
 * @throws ReportAPIError if the request fails
 */
export async function generateReport(
  companyName: string,
  startDate: Date,
  endDate: Date,
  agentType: SearchAgentType
): Promise<Blob> {
  const requestBody: ReportRequest = {
    company_name: companyName,
    start_date: formatDateForAPI(startDate),
    end_date: formatDateForAPI(endDate),
    agent_type: agentType,
  };

  const response = await apiFetch("/api/report/generate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    let errorMessage = "Rapor oluşturulurken bir hata oluştu";
    let details: string | undefined;

    try {
      const errorData = await response.json();
      details = errorData.detail || JSON.stringify(errorData);
    } catch {
      // Response is not JSON, use status text
      details = response.statusText;
    }

    throw new ReportAPIError(errorMessage, response.status, details);
  }

  // Return the PDF as a Blob
  return response.blob();
}

/**
 * Downloads a Blob as a file
 * @param blob - The Blob to download
 * @param filename - The filename for the download
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

/**
 * Opens a Blob in a new browser tab
 * @param blob - The Blob to open
 */
export function openBlobInNewTab(blob: Blob): void {
  const url = window.URL.createObjectURL(blob);
  window.open(url, "_blank");
  // Note: We don't revoke immediately as the new tab needs the URL
  // The browser will clean up when the tab is closed
}


// Tip tanımları
export interface ReportListItem {
  id: number;
  company_name: string;
  status: string | null;
  created_at: string;
}

export interface ReportListResponse {
  reports: ReportListItem[];
  total: number;
}

export interface ReportDetail {
  id: number;
  company_name: string;
  status: string | null;
  content: string | null;
  final_summary: string | null;
  created_at: string;
}

/**
 * Tüm raporları getirir
 */
export async function fetchReports(): Promise<ReportListResponse> {
  const response = await apiFetch("/api/report/list");

  if (!response.ok) {
    throw new ReportAPIError("Raporlar getirilirken hata oluştu", response.status);
  }

  return response.json();
}

/**
 * Belirli bir raporun detaylarını getirir
 */
export async function fetchReportById(reportId: number): Promise<ReportDetail> {
  const response = await apiFetch(`/api/report/${reportId}`);

  if (!response.ok) {
    throw new ReportAPIError("Rapor detayları getirilirken hata oluştu", response.status);
  }

  return response.json();
}
