"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Activity, Calendar, Download, Eye, FileText, Search, Trash2, Clock, MoreVertical } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { fetchReports, ReportListItem } from "@/lib/api/report-api"

// Sadece tamamlanan raporları içeren örnek veri
const mockReports = [
    {
        id: 1,
        companyName: "TechDynamics Solutions",
        dateRange: "01 Kas 2024 - 01 Ara 2025",
        createdDate: "10 Ara 2025",
        status: "Tamamlandı",
        agent: "Deep Search",
    },
    {
        id: 2,
        companyName: "Global Construction Ltd.",
        dateRange: "01 Oca 2023 - 01 Oca 2024",
        createdDate: "08 Ara 2025",
        status: "Tamamlandı",
        agent: "Standard",
    },
    {
        id: 3,
        companyName: "Future Energy Systems",
        dateRange: "15 Haz 2025 - 15 Ara 2025",
        createdDate: "05 Ara 2025",
        status: "Tamamlandı",
        agent: "Deep Search",
    },
    {
        id: 4,
        companyName: "BlueSky Logistics",
        dateRange: "01 Eyl 2024 - 30 Eyl 2024",
        createdDate: "01 Ara 2025",
        status: "Tamamlandı",
        agent: "Standard",
    },
]

export default function HistoryPage() {
    const [searchTerm, setSearchTerm] = useState("")
    const [reports, setReports] = useState<ReportListItem[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        async function loadReports() {
            try {
                setLoading(true)
                const data = await fetchReports()
                setReports(data.reports)
            } catch (err) {
                setError("Raporlar yüklenirken bir hata oluştu")
                console.error(err)
            } finally {
                setLoading(false)
            }
        }

        loadReports()
    }, [])

    const filteredReports = reports.filter((report) =>
        report.company_name.toLowerCase().includes(searchTerm.toLowerCase())
    )


    return (
        <div className="min-h-screen w-full bg-[#151a30] text-white overflow-x-hidden">

            {/* --- Header --- */}
            <header className="border-b border-white/10 bg-[#0a0e1a]/80 backdrop-blur-md sticky top-0 z-50 w-full">
                <nav className="container mx-auto px-4 h-16 flex items-center justify-between">
                    <Link href="/" className="flex items-center gap-2 text-xl font-bold group">
                        <Activity className="h-6 w-6 text-orange-500 group-hover:scale-110 transition-transform" />
                        <span>Sigmoid-rm</span>
                    </Link>

                    <div className="flex items-center gap-4">
                        {/* Sadece Ana Sayfa butonu kaldı */}
                        <Link href="/">
                            <Button variant="ghost" className="border border-grey-500 text-gray-400 hover:text-white hover:bg-white/5">
                                Ana Sayfa
                            </Button>
                        </Link>
                    </div>
                </nav>
            </header>

            {/* --- Main Content --- */}
            <main className="container mx-auto px-4 py-12">

                {/* Başlık ve Arama */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-10">
                    <div>
                        <h1 className="text-3xl font-bold text-white mb-2">Geçmiş Raporlar</h1>
                        <p className="text-gray-400">Tamamlanan tüm analizlerinize buradan erişebilirsiniz.</p>
                    </div>

                    <div className="relative w-full md:w-96">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                        <Input
                            placeholder="Şirket adı ara..."
                            className="pl-10 bg-[#111827] border-white/10 text-white focus-visible:ring-orange-500 h-12"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>
                </div>

                {/* --- Rapor Listesi --- */}
                {filteredReports.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                        {filteredReports.map((report) => (
                            <div
                                key={report.id}
                                className="group bg-[#0a0e1a] border border-white/10 rounded-xl p-6 hover:border-orange-500/50 transition-all duration-300 hover:shadow-[0_0_20px_rgba(249,115,22,0.1)] flex flex-col justify-between h-full min-h-[300px]"
                            >
                                {/* Üst Kısım */}
                                <div>
                                    <div className="flex items-start justify-between mb-4">
                                        <div className="w-12 h-12 rounded-lg bg-orange-500/10 flex items-center justify-center border border-orange-500/20 group-hover:bg-orange-500/20 transition-colors shrink-0">
                                            <FileText className="h-6 w-6 text-orange-500" />
                                        </div>
                                    </div>

                                    <h3 className="text-xl font-bold text-white mb-1 break-words" title={report.company_name}>
                                        {report.company_name}
                                    </h3>
                                    <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500 mb-4 mt-2">
                                        <Badge variant="secondary" className="bg-white/5 text-gray-400 hover:bg-white/10 font-normal whitespace-nowrap">
                                            {report.status}
                                        </Badge>
                                    </div>
                                </div>

                                {/* Alt Kısım */}
                                <div className="mt-4">
                                    <div className="flex items-center gap-2 text-sm text-gray-400 mb-6 bg-[#0a0e1a]/50 p-2 rounded-lg border border-white/5">
                                        <Calendar className="h-4 w-4 text-orange-500 shrink-0" />
                                        <span className="truncate">{report.created_at}</span>
                                    </div>

                                    <div className="flex items-center gap-3">
                                        {/* Artık kontrol yok, hepsi tamamlandı kabul ediliyor */}
                                        <Link href={`/report/${report.id}`} className="flex-1">
                                            <Button className="w-full bg-white/5 hover:bg-orange-600 hover:text-white text-gray-300 border border-white/10 hover:border-orange-500/50 transition-all">
                                                <Eye className="mr-2 h-4 w-4" /> Görüntüle
                                            </Button>
                                        </Link>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="flex flex-col items-center justify-center py-20 text-center border border-dashed border-white/10 rounded-2xl bg-[#111827]/50">
                        <div className="w-20 h-20 rounded-full bg-white/5 flex items-center justify-center mb-6">
                            <Search className="h-10 w-10 text-gray-600" />
                        </div>
                        <h3 className="text-xl font-bold text-white mb-2">Henüz Rapor Bulunamadı</h3>
                        <p className="text-gray-400 max-w-md mb-8">
                            Aradığınız kriterlere uygun rapor yok.
                        </p>
                        <Link href="/">
                            <Button className="bg-orange-600 hover:bg-orange-700 text-white px-8">
                                Ana Sayfaya Dön
                            </Button>
                        </Link>
                    </div>
                )}
            </main>
        </div>
    )
}