import { useEffect, useMemo, useRef, useState } from 'react';
import { formatCompactMoney, formatMoney, formatMonth } from '../../../shared/format.js';

const PAD = { top: 18, right: 14, bottom: 43, left: 76 };

export default function MonthlyChart({ totals, isUpdating }) {
  const [activeIndex, setActiveIndex] = useState(null);
  const containerRef = useRef(null);
  const [width, setWidth] = useState(660);
  const height = Math.round(Math.min(258, Math.max(180, width * 0.46)));

  useEffect(() => {
    const observer = new ResizeObserver(([entry]) => {
      if (entry.contentRect.width > 0) setWidth(Math.max(280, Math.round(entry.contentRect.width)));
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  const chartData = useMemo(() => {
    const maxAmount = Math.max(0, ...totals.map((item) => Number(item.amount_due)));
    const minAmount = Math.min(0, ...totals.map((item) => Number(item.amount_due)));
    const scaleMax = maxAmount > 0 ? maxAmount * 1.15 : 0;
    const scaleMin = minAmount < 0 ? minAmount * 1.15 : 0;
    const range = scaleMax - scaleMin || 1;
    const plotWidth = width - PAD.left - PAD.right;
    const plotHeight = height - PAD.top - PAD.bottom;
    const slotWidth = plotWidth / Math.max(totals.length, 1);
    const bars = totals.map((item, index) => ({
      ...item,
      value: Number(item.amount_due),
      x: PAD.left + slotWidth * index + slotWidth / 2,
      y: PAD.top + plotHeight * ((scaleMax - Number(item.amount_due)) / range),
      height: plotHeight * (Math.abs(Number(item.amount_due)) / range),
      rectY: Math.min(
        PAD.top + plotHeight * ((scaleMax - Number(item.amount_due)) / range),
        PAD.top + plotHeight * (scaleMax / range),
      ),
      width: Math.min(slotWidth * 0.62, 38),
      slotX: PAD.left + slotWidth * index,
    }));
    const ticks = [0, 1, 2, 3].map((index) => ({
      y: PAD.top + (plotHeight * index) / 3,
      value: scaleMax - range * (index / 3),
    }));
    return { bars, plotHeight, slotWidth, ticks };
  }, [totals, width, height]);

  const activeBar = activeIndex === null ? null : chartData.bars[activeIndex];
  const labelEvery = Math.max(
    1,
    Math.ceil(totals.length / Math.max(2, Math.floor((width - PAD.left - PAD.right) / 65))),
  );

  return (
    <div ref={containerRef} className={`chart-visual${isUpdating ? ' is-updating' : ''}`}>
      <svg
        className="monthly-chart"
        viewBox={`0 0 ${width} ${height}`}
        role="group"
        aria-label="Gráfico de barras dos valores de cobranças por mês. Selecione ou aponte para uma barra para consultar o valor."
      >
        {chartData.ticks.map((tick, index) => (
          <g key={index} aria-hidden="true">
            <line
              x1={PAD.left}
              x2={width - PAD.right}
              y1={tick.y}
              y2={tick.y}
              className="chart-gridline"
            />
            <text x={PAD.left - 10} y={tick.y + 4} className="chart-y-label" textAnchor="end">
              {formatCompactMoney(tick.value)}
            </text>
          </g>
        ))}
        {chartData.bars.map((bar, index) => (
          <g
            key={bar.month}
            className={`chart-bar${activeIndex === index ? ' is-active' : ''}`}
            tabIndex="0"
            role="button"
            aria-label={`${formatMonth(bar.month)}: ${formatMoney(bar.amount_due)}`}
            onPointerEnter={() => setActiveIndex(index)}
            onFocus={() => setActiveIndex(index)}
            onBlur={() => setActiveIndex(null)}
          >
            <rect
              x={bar.slotX}
              y={PAD.top}
              width={chartData.slotWidth}
              height={chartData.plotHeight}
              className="chart-bar-hit-area"
            />
            <rect
              x={bar.x - bar.width / 2}
              y={bar.rectY}
              width={bar.width}
              height={bar.height}
              rx="5"
              className="monthly-bar"
            />
            <title>
              {formatMonth(bar.month)} · {formatMoney(bar.amount_due)}
            </title>
          </g>
        ))}
        {chartData.bars
          .filter((_, index) => index % labelEvery === 0 || index === chartData.bars.length - 1)
          .map((bar) => (
            <text
              key={bar.month}
              x={bar.x}
              y={height - 13}
              className="chart-x-label"
              textAnchor="middle"
              aria-hidden="true"
            >
              {formatMonth(bar.month)}
            </text>
          ))}
      </svg>
      <p className="chart-tooltip" role="status" aria-live="polite">
        {activeBar ? (
          <>
            <strong>{formatMonth(activeBar.month)}</strong>
            <span>{formatMoney(activeBar.amount_due)}</span>
          </>
        ) : (
          'Aponte para uma barra ou use a tecla Tab para ver o valor.'
        )}
      </p>
      <details className="chart-data-table">
        <summary>Ver valores em tabela</summary>
        <table>
          <caption>Valor das cobranças por mês no período selecionado</caption>
          <thead>
            <tr>
              <th>Mês</th>
              <th>Valor</th>
            </tr>
          </thead>
          <tbody>
            {totals.map((item) => (
              <tr key={item.month}>
                <th scope="row">{formatMonth(item.month)}</th>
                <td>{formatMoney(item.amount_due)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}
