"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Flame, MapPin, Building2, TrendingUp } from "lucide-react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { getToken } from "@/lib/auth"

interface DemandItem {
    region: string
    type: string
    score: number
}

export function DemandHeatmapWidget() {
    const [data, setData] = useState<DemandItem[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        async function fetchData() {
            try {
                const token = getToken()
                if (!token) return

                const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/dashboard/demand-heatmap?limit=8`, {
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                })

                if (res.ok) {
                    const json = await res.json()
                    setData(json)
                }
            } catch (error) {
                console.error("Falha ao buscar heatmap de demanda", error)
            } finally {
                setLoading(false)
            }
        }

        fetchData()
    }, [])

    const maxScore = data.length > 0 ? Math.max(...data.map(d => d.score)) : 0

    return (
        <Card className="col-span-4 lg:col-span-3 overflow-hidden border-orange-100 bg-gradient-to-br from-white to-orange-50/30">
            <CardHeader
                title={
                    <div className="flex items-center gap-2">
                        <div className="p-2 bg-orange-100 rounded-lg">
                            <Flame className="w-5 h-5 text-orange-600" />
                        </div>
                        <span>Mapa de Calor da Demanda</span>
                    </div>
                }
                subtitle="O que os clientes estão buscando agora"
                action={
                    <Badge variant="outline" className="bg-orange-50 text-orange-700 border-orange-200 gap-1">
                        <TrendingUp className="w-3 h-3" />
                        Em Alta
                    </Badge>
                }
            />

            <CardContent className="p-0">
                <ScrollArea className="h-[300px] px-6 pb-6">
                    {loading ? (
                        <div className="space-y-3 mt-4">
                            {[1, 2, 3, 4].map((i) => (
                                <div key={i} className="h-12 w-full bg-gray-100 animate-pulse rounded-xl" />
                            ))}
                        </div>
                    ) : data.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-12 text-center text-gray-500">
                            <MapPin className="w-10 h-10 mb-2 opacity-20" />
                            <p>Ainda sem dados suficientes para gerar o mapa.</p>
                        </div>
                    ) : (
                        <div className="mt-4 space-y-3">
                            {data.map((item, index) => {
                                const percentage = Math.round((item.score / maxScore) * 100)

                                return (
                                    <div key={index} className="group relative">
                                        {/* Background Progress Bar */}
                                        <div
                                            className="absolute inset-0 bg-orange-100/40 rounded-xl transition-all duration-500 ease-out"
                                            style={{ width: `${percentage}%` }}
                                        />

                                        <div className="relative flex items-center justify-between p-3 rounded-xl border border-orange-100/50 bg-white/40 backdrop-blur-sm hover:bg-white/60 transition-colors">
                                            <div className="flex items-center gap-3">
                                                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-white shadow-sm text-sm font-bold text-orange-600 border border-orange-100">
                                                    #{index + 1}
                                                </div>

                                                <div className="flex flex-col">
                                                    <span className="font-semibold text-gray-800 flex items-center gap-1.5">
                                                        {item.region}
                                                    </span>
                                                    <span className="text-xs text-gray-500 flex items-center gap-1">
                                                        <Building2 className="w-3 h-3" />
                                                        {item.type}
                                                    </span>
                                                </div>
                                            </div>

                                            <div className="flex flex-col items-end">
                                                <span className="text-sm font-bold text-orange-700">
                                                    {percentage}%
                                                </span>
                                                <span className="text-[10px] uppercase font-medium text-orange-600/70">
                                                    Intensidade
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    )}
                </ScrollArea>
            </CardContent>
        </Card>
    )
}
