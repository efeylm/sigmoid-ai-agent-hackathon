"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { ArrowLeft, Download, FileText, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"

/**
 * Report Page - Displays the generated PDF report
 * Reads PDF data from sessionStorage (set by the home page after report generation)
 */
export default function ReportPage() {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [companyName, setCompanyName] = useState<string>("Şirket Raporu")
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // AI-generated: Read PDF data from sessionStorage
    try {
      const storedCompanyName = sessionStorage.getItem("reportCompanyName")
      const storedPdfBase64 = sessionStorage.getItem("reportPdfData")

      if (storedCompanyName) {
        setCompanyName(storedCompanyName)
      }

      if (storedPdfBase64) {
        // Convert base64 back to blob URL
        const byteCharacters = atob(storedPdfBase64)
        const byteNumbers = new Array(byteCharacters.length)
        for (let i = 0; i < byteCharacters.length; i++) {
          byteNumbers[i] = byteCharacters.charCodeAt(i)
        }
        const byteArray = new Uint8Array(byteNumbers)
        const blob = new Blob([byteArray], { type: "application/pdf" })
        const url = URL.createObjectURL(blob)
        setPdfUrl(url)
      } else {
        setError("PDF verisi bulunamadı. Lütfen ana sayfadan rapor oluşturun.")
      }
    } catch (err) {
      console.error("Error loading PDF:", err)
      setError("PDF yüklenirken bir hata oluştu.")
    } finally {
      setIsLoading(false)
    }

    // Cleanup blob URL on unmount
    return () => {
      if (pdfUrl) {
        URL.revokeObjectURL(pdfUrl)
      }
    }
  }, [])

  const handleDownload = () => {
    if (!pdfUrl) return

    const link = document.createElement("a")
    link.href = pdfUrl
    link.download = `${companyName.replace(/\s+/g, "_")}_Report.pdf`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <div className="h-screen bg-[#151a30] text-white flex flex-col overflow-hidden">
      {/* --- Header --- */}
      <header className="h-16 border-b border-white/10 bg-[#0a0e1a] flex items-center shrink-0 z-10 relative">
        <div className="container mx-auto px-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors">
              <ArrowLeft className="h-5 w-5" />
              <span className="hidden sm:inline">Geri Dön</span>
            </Link>
            <div className="h-6 w-px bg-white/10 mx-2" />
            <div className="flex items-center gap-2 font-semibold">
              <FileText className="h-5 w-5 text-orange-400" />
              <span>Rapor: {companyName}</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button
              onClick={handleDownload}
              disabled={!pdfUrl}
              className="bg-orange-600 hover:bg-orange-700 text-white border-none disabled:opacity-50"
            >
              <Download className="h-4 w-4 mr-2" />
              PDF'yi İndir
            </Button>
          </div>
        </div>
      </header>

      {/* --- Main Content: PDF Viewer --- */}
      <main className="flex-1 bg-[#111827] relative w-full h-full">
        {isLoading ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-400">
            <Loader2 className="h-8 w-8 animate-spin mb-4" />
            <p>PDF yükleniyor...</p>
          </div>
        ) : error ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-400">
            <FileText className="h-12 w-12 mb-4 text-red-400" />
            <p className="text-red-400 mb-4">{error}</p>
            <Link href="/">
              <Button className="bg-orange-600 hover:bg-orange-700">
                Ana Sayfaya Dön
              </Button>
            </Link>
          </div>
        ) : pdfUrl ? (
          <div className="absolute inset-0 w-full h-full">
            <iframe
              src={`${pdfUrl}#toolbar=1&navpanes=0&scrollbar=1`}
              className="w-full h-full border-none"
              title="Company Report PDF"
            />
          </div>
        ) : null}
      </main>
    </div>
  )
}
