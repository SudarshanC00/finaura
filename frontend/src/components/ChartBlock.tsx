"use client";

import React from "react";
import {
    BarChart,
    Bar,
    LineChart,
    Line,
    PieChart,
    Pie,
    Cell,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from "recharts";
import type { PieLabelRenderProps } from "recharts";
import { ChartData } from "@/lib/types";

const COLORS = [
    "#0D9488", // teal (primary)
    "#F59E0B", // amber (secondary)
    "#6366F1", // indigo
    "#EF4444", // red
    "#8B5CF6", // violet
    "#EC4899", // pink
    "#14B8A6", // teal-light
    "#F97316", // orange
];

const tooltipStyle = {
    background: "var(--chart-tooltip-bg)",
    border: "1px solid var(--chart-tooltip-border)",
    borderRadius: 8,
    color: "var(--chart-tooltip-text)",
    fontSize: "13px",
};

interface ChartBlockProps {
    chart: ChartData;
}

export default function ChartBlock({ chart }: ChartBlockProps) {
    const { type, title, data, xKey = "name", yKeys = ["value"] } = chart;

    if (!data || data.length === 0) return null;

    const axisProps = {
        tick: { fill: "var(--chart-axis)", fontSize: 11 },
        axisLine: { stroke: "var(--chart-grid)" },
    };

    return (
        <div className="chart-block">
            {title && <div className="chart-block__title">{title}</div>}
            <div className="chart-block__container">
                <ResponsiveContainer width="100%" height={260}>
                    {type === "pie" ? (
                        <PieChart>
                            <Pie
                                data={data}
                                dataKey="value"
                                nameKey="name"
                                cx="50%"
                                cy="50%"
                                outerRadius={95}
                                label={(props: PieLabelRenderProps) => {
                                    const name = String(props.name ?? "");
                                    const pct = Number(props.percent ?? 0);
                                    return `${name} ${(pct * 100).toFixed(0)}%`;
                                }}
                                labelLine
                            >
                                {data.map((_, i) => (
                                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                                ))}
                            </Pie>
                            <Tooltip contentStyle={tooltipStyle} />
                            <Legend wrapperStyle={{ fontSize: "12px" }} />
                        </PieChart>
                    ) : type === "line" ? (
                        <LineChart data={data}>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                            <XAxis dataKey={xKey} {...axisProps} />
                            <YAxis {...axisProps} />
                            <Tooltip contentStyle={tooltipStyle} />
                            <Legend wrapperStyle={{ fontSize: "12px" }} />
                            {yKeys.map((key, i) => (
                                <Line
                                    key={key}
                                    type="monotone"
                                    dataKey={key}
                                    stroke={COLORS[i % COLORS.length]}
                                    strokeWidth={2}
                                    dot={{ fill: COLORS[i % COLORS.length], r: 3 }}
                                    activeDot={{ r: 5 }}
                                />
                            ))}
                        </LineChart>
                    ) : (
                        <BarChart data={data}>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                            <XAxis dataKey={xKey} {...axisProps} />
                            <YAxis {...axisProps} />
                            <Tooltip contentStyle={tooltipStyle} />
                            <Legend wrapperStyle={{ fontSize: "12px" }} />
                            {yKeys.map((key, i) => (
                                <Bar
                                    key={key}
                                    dataKey={key}
                                    fill={COLORS[i % COLORS.length]}
                                    radius={[4, 4, 0, 0]}
                                />
                            ))}
                        </BarChart>
                    )}
                </ResponsiveContainer>
            </div>
        </div>
    );
}
