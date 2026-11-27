"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Activity, BarChart3, FileText } from "lucide-react"
import Link from "next/link"
import { DateRangePicker } from "@/components/date-range-picker"
import { useRouter } from "next/navigation"
import { DateRange } from "react-day-picker"
import { subYears } from "date-fns"
import { SearchAgentType } from "@/lib/types/report"
import { generateReport, ReportAPIError } from "@/lib/api/report-api"

export default function HomePage() {
  const router = useRouter()

  // State Tanımları
  const [companyName, setCompanyName] = useState("")
  const [date, setDate] = useState<DateRange | undefined>()
  const [agentChoice, setAgentChoice] = useState<SearchAgentType>("TAVILY")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const today = new Date()
  const minDate = new Date("2022-01-01")
  const threeYearsAgo = subYears(today, 3)
  const isFormValid = companyName.trim().length > 0 && date?.from && date?.to

  const handleGenerateReport = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isFormValid || !date?.from || !date?.to) return

    setIsLoading(true)
    setError(null)

    try {
      // AI-generated: Call backend API to generate PDF report
      const pdfBlob = await generateReport(
        companyName,
        date.from,
        date.to,
        "TAVILY"
      )

      // Convert blob to base64 and store in sessionStorage
      const reader = new FileReader()
      reader.onloadend = () => {
        const base64data = reader.result as string
        // Remove the data:application/pdf;base64, prefix
        const base64Only = base64data.split(",")[1]

        sessionStorage.setItem("reportCompanyName", companyName)
        sessionStorage.setItem("reportPdfData", base64Only)

        // Navigate to report page
        router.push("/report-page")
      }
      reader.readAsDataURL(pdfBlob)

    } catch (err) {
      console.error("Report generation error:", err)

      if (err instanceof ReportAPIError) {
        setError(`Hata (${err.statusCode}): ${err.details || err.message}`)
      } else if (err instanceof Error) {
        setError(`Bir hata oluştu: ${err.message}`)
      } else {
        setError("Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin.")
      }
      // Only reset loading on error - on success we navigate away
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#151a30] text-white">
      {/* Navigation */}
      <header className="border-b border-white/10">
        <nav className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 text-xl font-bold">
            {/* Logo Rengi Turuncu Oldu */}
            <Activity className="h-6 w-6 text-orange-500" />
            <span>Sigmoid-rm</span>
          </Link>
          <div className="flex items-center gap-8">
            <Link href="#features" className="text-gray-300 hover:text-white transition-colors">
              Özellikler
            </Link>
            <Link href="/my-reports" className="text-gray-300 hover:text-white transition-colors">
              Raporlar
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20">
        <div className="grid lg:grid-cols-2 gap-12 items-center mb-16">
          <div>
            <h1 className="text-7xl sm:text-8xl lg:text-8xl font-extrabold mb-8 text-balance leading-none tracking-tighter">
              Anında
              <br />
              <span className="text-[#ff6b00] animate-neon-orange">
                YZ Destekli
              </span>
              <br />
              Şirket
              <br />
              Raporu
            </h1>
            <p className="text-lg text-gray-400 text-pretty">
              Şirket haberleri, ihale hakları ve önemli veriler hakkında kapsamlı raporları saniyeler içinde alın.
              Bırakın yapay zekamız sizin için zor işleri yapsın.
            </p>
          </div>
          <div className="relative">
            {/* Arka plan parlama efekti turuncu/kırmızı yapıldı */}
            <div className="absolute inset-0 bg-gradient-to-br from-orange-500/20 to-red-600/20 rounded-3xl blur-3xl" />
            <div className="relative aspect-[4/3] rounded-3xl border-2 border-orange-500/30 overflow-hidden">
              <img
                src="/images/hero-illustration.svg"
                alt="AI Technology"
                className="w-full h-full object-cover"
              />
            </div>
          </div>
        </div>

        {/* --- FORM KISMI --- */}
        <div className="max-w-6xl mx-auto">
          <div className="bg-[#111827] border border-white/10 rounded-2xl p-6 md:p-8 shadow-2xl shadow-orange-900/10 relative z-10">
            <h2 className="text-4xl font-bold mb-6 text-center">Analize Başlayın</h2>

            <form onSubmit={handleGenerateReport} className="grid xl:grid-cols-[1.5fr,1fr,1.2fr,auto] gap-4 items-center">

              {/* 1. KISIM: ŞİRKET ADI */}
              <div className="relative w-full">
                <Input
                  type="text"
                  placeholder="Şirket adı girin..."
                  // Focus rengi turuncu yapıldı
                  className="bg-[#1a2332] border-white/10 text-white placeholder:text-gray-500 h-12 focus-visible:ring-orange-500 w-full"
                  required
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                />
              </div>

              {/* 2. KISIM: TARİH ARALIĞI */}
              <div className="w-full">
                <DateRangePicker
                  className="w-full"
                  date={date}
                  setDate={setDate}
                  disabledDates={{ after: today, before: minDate }}
                />
              </div>

              {/* 3. KISIM: AGENT SEÇİMİ */}
              <div className="flex items-center gap-3 w-full">
                <span className="text-lg font-medium text-gray-300 whitespace-nowrap">
                  İnternet Araması Ajanı:
                </span>

                <div className="h-12 bg-[#1a2332] rounded-md border border-white/10 p-1 flex gap-1 flex-1">
                  <button
                    type="button"
                    onClick={() => setAgentChoice("TAVILY")}
                    // Seçili alan için turuncu gradient kullanıldı
                    className={`flex-1 rounded text-sm font-medium transition-all duration-200 ${agentChoice === "TAVILY"
                      ? "bg-gradient-to-r from-orange-500 to-orange-600 text-white shadow-lg shadow-orange-500/20"
                      : "text-gray-400 hover:text-white hover:bg-white/5"
                      }`}
                  >
                    Tavily
                  </button>
                </div>
              </div>

              {/* 4. KISIM: BUTON */}
              <Button
                type="submit"
                disabled={!isFormValid || isLoading}
                // Buton rengi turuncudan kırmızıya çalan bir gölge efektiyle tasarlandı
                className="w-full md:w-auto bg-green-800 hover:bg-green-600 text-white h-12 text-lg font-semibold px-8 shadow-[0_0_20px_rgba(249,115,22,0.3)] hover:shadow-[0_0_30px_rgba(249,115,22,0.5)] transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
              >
                {isLoading ? "Rapor Oluşturuluyor..." : "Rapor Oluştur"}
              </Button>
            </form>

            {/* Hata Mesajı */}
            {error && (
              <div className="mt-4 p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm">
                {error}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* --- FEATURES SECTION (ARTIK DÖNEN KARTLAR BURADA) --- */}
      <section id="features" className="container mx-auto px-4 py-20 border-t border-white/5">
        <div className="flex items-end justify-between mb-12">
          <div>
            <h2 className="text-4xl font-bold mb-4">Benzersiz Analizlere Ulaşın</h2>
            <p className="text-gray-400 max-w-2xl">
              En ileri yapay zeka teknolojimiz,
              daha akıllı kararlar almanız için ihtiyaç duyduğunuz kritik bilgileri daha hızlı bir şekilde sunar.
            </p>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-6">

          {/* Kart 1: Historical News Analysis (Dönen Kart) */}
          <div className="group h-80 [perspective:1000px]">
            <div className="relative h-full w-full transition-all duration-700 [transform-style:preserve-3d] group-hover:[transform:rotateY(180deg)]">
              {/* ÖN YÜZ */}
              <div className="absolute inset-0 h-full w-full flex flex-col items-center justify-center rounded-2xl bg-[#111827] border border-white/10 p-8 shadow-xl [backface-visibility:hidden]">
                <div className="w-16 h-16 rounded-lg bg-orange-500/10 flex items-center justify-center mb-6 border border-orange-500/20">
                  <FileText className="h-8 w-8 text-orange-500" />
                </div>
                <h3 className="text-2xl font-bold text-white text-center">Son 3 Yılın Haber Analizi</h3>
              </div>
              {/* ARKA YÜZ */}
              <div className="absolute inset-0 h-full w-full flex items-center justify-center rounded-2xl bg-gradient-to-br from-[#111827] to-orange-900/20 border border-orange-500/50 p-8 text-center [transform:rotateY(180deg)] [backface-visibility:hidden]">
                <p className="text-gray-300 text-lg leading-relaxed">
                  Son üç yıla yayılan şirket özelindeki haberleri ve olayları değerlendirerek derinlemesine bilgi edinin.
                </p>
              </div>
            </div>
          </div>

          {/* Kart 2: Tender Eligibility Check (Dönen Kart) */}
          <div className="group h-80 [perspective:1000px]">
            <div className="relative h-full w-full transition-all duration-700 [transform-style:preserve-3d] group-hover:[transform:rotateY(180deg)]">
              {/* ÖN YÜZ */}
              <div className="absolute inset-0 h-full w-full flex flex-col items-center justify-center rounded-2xl bg-[#111827] border border-white/10 p-8 shadow-xl [backface-visibility:hidden]">
                <div className="w-16 h-16 rounded-lg bg-orange-500/10 flex items-center justify-center mb-6 border border-orange-500/20">
                  <Activity className="h-8 w-8 text-orange-500" />
                </div>
                <h3 className="text-2xl font-bold text-white text-center">İhale Yasaklısı Kararı Bilgisi</h3>
              </div>
              {/* ARKA YÜZ */}
              <div className="absolute inset-0 h-full w-full flex items-center justify-center rounded-2xl bg-gradient-to-br from-[#111827] to-orange-900/20 border border-orange-500/50 p-8 text-center [transform:rotateY(180deg)] [backface-visibility:hidden]">
                <p className="text-gray-300 text-lg leading-relaxed">
                  Resmi kayıtlardaki aktif yasakları ve kısıtlamaları kontrol ederek ihale uygunluğunu anında doğrulayın.
                </p>
              </div>
            </div>
          </div>

          {/* Kart 3: Corporate Registry Intelligence (Dönen Kart) */}
          <div className="group h-80 [perspective:1000px]">
            <div className="relative h-full w-full transition-all duration-700 [transform-style:preserve-3d] group-hover:[transform:rotateY(180deg)]">
              {/* ÖN YÜZ */}
              <div className="absolute inset-0 h-full w-full flex flex-col items-center justify-center rounded-2xl bg-[#111827] border border-white/10 p-8 shadow-xl [backface-visibility:hidden]">
                <div className="w-16 h-16 rounded-lg bg-orange-500/10 flex items-center justify-center mb-6 border border-orange-500/20">
                  <BarChart3 className="h-8 w-8 text-orange-500" />
                </div>
                <h3 className="text-2xl font-bold text-white text-center">Kurumsal Kayıt İstihbaratı</h3>
              </div>
              {/* ARKA YÜZ */}
              <div className="absolute inset-0 h-full w-full flex items-center justify-center rounded-2xl bg-gradient-to-br from-[#111827] to-orange-900/20 border border-orange-500/50 p-8 text-center [transform:rotateY(180deg)] [backface-visibility:hidden]">
                <p className="text-gray-300 text-lg leading-relaxed">
                  Hisse devirleri ve adres güncellemeleri de dahil olmak üzere hayati kurumsal değişiklikleri doğrudan Resmi Gazete'den takip edin.
                </p>
              </div>
            </div>
          </div>

        </div>
      </section>

      {/* --- HOW IT WORKS SECTION (ARTIK SABİT KARTLAR BURADA) --- */}
      <section className="container mx-auto px-4 pt-20 pb-8">
        <h2 className="text-4xl font-bold text-center mb-12">3 Basit Adımda Raporunuz Hazır</h2>

        <div className="grid md:grid-cols-3 gap-6">

          {/* Adım 1 (Sabit Kart) */}
          <Card className="bg-[#111827] border-white/10 hover:border-orange-500/50 transition-colors group h-full">
            <CardContent className="p-8 flex flex-col items-center text-center h-full">
              <div className="w-16 h-16 rounded-full bg-orange-500/10 border-2 border-orange-500 flex items-center justify-center mb-6 shadow-[0_0_15px_rgba(249,115,22,0.2)] group-hover:bg-orange-500/20 transition-colors">
                <span className="text-3xl font-bold text-orange-500">1</span>
              </div>
              <h3 className="text-2xl font-bold mb-3 text-white">Şirket Adı ve Tarih Aralığı Girin</h3>
              <p className="text-gray-400">Raporunuz için şirket adını ve tarih aralığını belirtin. Birden fazla kayıt defterinde küresel aramayı destekliyoruz.</p>
            </CardContent>
          </Card>

          {/* Adım 2 (Sabit Kart) */}
          <Card className="bg-[#111827] border-white/10 hover:border-orange-500/50 transition-colors group h-full">
            <CardContent className="p-8 flex flex-col items-center text-center h-full">
              <div className="w-16 h-16 rounded-full bg-orange-500/10 border-2 border-orange-500 flex items-center justify-center mb-6 shadow-[0_0_15px_rgba(249,115,22,0.2)] group-hover:bg-orange-500/20 transition-colors">
                <span className="text-3xl font-bold text-orange-500">2</span>
              </div>
              <h3 className="text-2xl font-bold mb-3 text-white">YZ Arkaplanda Tarama Yapsın</h3>
              <p className="text-gray-400">Güçlü yapay zekamız, önemli bilgiler elde etmek için milyonlarca veri noktasını, haber makalesini ve Resmi Gazete'yi saniyeler içinde tarar.</p>
            </CardContent>
          </Card>

          {/* Adım 3 (Sabit Kart) */}
          <Card className="bg-[#111827] border-white/10 hover:border-orange-500/50 transition-colors group h-full">
            <CardContent className="p-8 flex flex-col items-center text-center h-full">
              <div className="w-16 h-16 rounded-full bg-orange-500/10 border-2 border-orange-500 flex items-center justify-center mb-6 shadow-[0_0_15px_rgba(249,115,22,0.2)] group-hover:bg-orange-500/20 transition-colors">
                <span className="text-3xl font-bold text-orange-500">3</span>
              </div>
              <h3 className="text-2xl font-bold mb-3 text-white">Raporunuz Hazır</h3>
              <p className="text-gray-400">Kapsamlı ve kolay okunabilir bir PDF raporunu anında görüntüleyin. Sunum ve karar verme için hazır.</p>
            </CardContent>
          </Card>

        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 py-8 mt-12">
        <div className="container mx-auto px-4 flex flex-col md:flex-row items-center justify-between text-sm text-gray-400 gap-4">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-orange-500" />
            <span>© 2025 Sigmoid-rm. Tüm hakları saklıdır.</span>
          </div>
        </div>
      </footer>
    </div>
  )
}