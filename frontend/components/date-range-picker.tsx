"use client"

import * as React from "react"
import { format, subMonths, subYears } from "date-fns"
import { tr } from "date-fns/locale" // TÜRKÇE LOCALE EKLENDİ
import { Calendar as CalendarIcon } from "lucide-react"
import { DateRange, Matcher } from "react-day-picker"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"

interface DateRangePickerProps extends React.HTMLAttributes<HTMLDivElement> {
  date: DateRange | undefined
  setDate: (date: DateRange | undefined) => void
  disabledDates?: Matcher | Matcher[]
  placeholder?: string
}

export function DateRangePicker({
  className,
  date,
  setDate,
  disabledDates,
}: DateRangePickerProps) {

  const handlePresetSelect = (preset: '1month' | '1year' | '3years') => {
    const today = new Date()
    let fromDate = new Date()

    switch (preset) {
      case '1month':
        fromDate = subMonths(today, 1)
        break
      case '1year':
        fromDate = subYears(today, 1)
        break
      case '3years':
        fromDate = subYears(today, 3)
        break
    }

    setDate({
      from: fromDate,
      to: today
    })
  }

  return (
    <div className={cn("grid gap-2", className)}>
      <Popover>
        <PopoverTrigger asChild>
          <Button
            id="date"
            variant={"outline"}
            className={cn(
              "w-full justify-start text-left font-normal h-12",
              "bg-[#1a2332] border-white/10 text-white hover:bg-[#1a2332]/80 hover:text-orange-500 hover:border-orange-500/50 transition-all",
              !date && "text-muted-foreground"
            )}
          >
            <CalendarIcon className="mr-2 h-4 w-4 text-orange-500" />
            {date?.from ? (
              date.to ? (
                <>
                  {format(date.from, "dd MMM yyyy", { locale: tr })} -{" "}
                  {format(date.to, "dd MMM yyyy", { locale: tr })}
                </>
              ) : (
                format(date.from, "dd MMM yyyy", { locale: tr })
              )
            ) : (
              <span className="text-gray-500">Tarih aralığı girin...</span>
            )}
          </Button>
        </PopoverTrigger>

        <PopoverContent className="w-auto p-0 bg-[#111827] border-white/10" align="start">

          {/* Preset Butonları */}
          <div className="flex items-center gap-2 p-3 border-b border-white/10">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handlePresetSelect('1month')}
              className="text-xs h-8 bg-white/5 hover:bg-orange-500 hover:text-white text-gray-300 transition-colors"
            >
              Son 1 Ay
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handlePresetSelect('1year')}
              className="text-xs h-8 bg-white/5 hover:bg-orange-500 hover:text-white text-gray-300 transition-colors"
            >
              Son 1 Yıl
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handlePresetSelect('3years')}
              className="text-xs h-8 bg-white/5 hover:bg-orange-500 hover:text-white text-gray-300 transition-colors"
            >
              Son 3 Yıl
            </Button>
          </div>

          <Calendar
            initialFocus
            mode="range"
            defaultMonth={date?.from}
            selected={date}
            onSelect={setDate}
            numberOfMonths={2}
            disabled={disabledDates}
            captionLayout="dropdown" // ← YIL VE AY SEÇİCİ EKLENDI (dropdown = her ikisi)
            fromYear={2022} // ← Başlangıç yılı (ihtiyacınıza göre ayarlayın)
            toYear={new Date().getFullYear()} // ← Bitiş yılı (bugünkü yıl)
            className="text-white"
            classNames={{
              day_selected: "bg-orange-500 text-white hover:bg-orange-600 focus:bg-orange-500",
              day_today: "bg-white/10 text-white",
              day_range_middle: "aria-selected:bg-orange-500/20 aria-selected:text-white",
              day_disabled: "text-gray-600 opacity-50 cursor-not-allowed hover:bg-transparent hover:text-gray-600",
            }}
          />
        </PopoverContent>
      </Popover>
    </div>
  )
}