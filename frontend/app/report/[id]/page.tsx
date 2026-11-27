"use client"

import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import Link from "next/link"
import { ArrowLeft, Download, FileText, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { apiFetch } from "@/lib/api/access"


export default function ReportDetailPage() {
    const params = useParams()
    const reportId = params.id

    const [pdfUrl, setPdfUrl] = useState<string | null>(null)
    const [companyName, setCompanyName] = useState<string>("Şirket Raporu")
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        async function loadPdf() {
            try {
                setIsLoading(true)

                // Önce rapor bilgisini al (şirket adı için)
                const infoRes = await apiFetch(`/api/report/${reportId}`)
                if (infoRes.ok) {
                    const info = await infoRes.json()
                    setCompanyName(info.company_name)
                }

                // PDF'i fetch et
                const pdfRes = await apiFetch(`/api/report/${reportId}/pdf`)

                if (!pdfRes.ok) {
                    throw new Error("PDF yüklenemedi")
                }

                const blob = await pdfRes.blob()
                const url = URL.createObjectURL(blob)
                setPdfUrl(url)

            } catch (err) {
                console.error("Error loading PDF:", err)
                setError("PDF yüklenirken bir hata oluştu.")
            } finally {
                setIsLoading(false)
            }
        }

        if (reportId) {
            loadPdf()
        }

        return () => {
            if (pdfUrl) {
                URL.revokeObjectURL(pdfUrl)
            }
        }
    }, [reportId])

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
                        <Link href="/my-reports" className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors">
                            <ArrowLeft className="h-5 w-5" />
                            <span className="hidden sm:inline">Raporlara Dön</span>
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
                        <Link href="/my-reports">
                            <Button className="bg-orange-600 hover:bg-orange-700">
                                Raporlara Dön
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