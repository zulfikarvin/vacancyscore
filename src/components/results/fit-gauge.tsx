"use client";

import { PolarAngleAxis, RadialBar, RadialBarChart } from "recharts";

/**
 * The fit score. Deliberately the largest thing on the screen.
 *
 * Recharts draws the ring; the gradient runs accent -> violet-300 across the
 * arc (SVG has no true conic gradient, and a linear sweep across a ring this
 * thick is visually identical).
 */
export function FitGauge({ score, size = 208 }: { score: number; size?: number }) {
  const data = [{ name: "fit", value: Math.max(0, Math.min(100, score)) }];

  return (
    <div
      className="relative shrink-0"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Fit score ${score} out of 100`}
    >
      <RadialBarChart
        width={size}
        height={size}
        data={data}
        innerRadius={size * 0.37}
        outerRadius={size * 0.5}
        startAngle={90}
        endAngle={-270}
      >
        <defs>
          <linearGradient id="gauge-fill" x1="0" y1="1" x2="1" y2="0">
            <stop offset="0%" stopColor="var(--color-accent)" />
            <stop offset="55%" stopColor="var(--color-accent-light)" />
            <stop offset="100%" stopColor="var(--color-violet-300)" />
          </linearGradient>
        </defs>
        <PolarAngleAxis
          type="number"
          domain={[0, 100]}
          angleAxisId={0}
          tick={false}
        />
        <RadialBar
          dataKey="value"
          angleAxisId={0}
          cornerRadius={999}
          fill="url(#gauge-fill)"
          background={{ fill: "rgba(255,255,255,0.08)" }}
          isAnimationActive
          animationDuration={900}
        />
      </RadialBarChart>

      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span className="tabular text-[64px] font-semibold leading-none tracking-tight text-white">
          {score}
        </span>
        <span className="mt-2 text-[11px] font-medium uppercase tracking-[0.18em] text-violet-200">
          out of 100
        </span>
      </div>
    </div>
  );
}
