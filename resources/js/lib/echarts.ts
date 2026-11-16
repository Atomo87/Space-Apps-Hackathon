// Registro modular do ECharts (só o que usamos → pacote menor para conexões fracas).
import { BarChart, LineChart, RadarChart, ScatterChart } from 'echarts/charts';
import { GridComponent, LegendComponent, MarkLineComponent, RadarComponent, TooltipComponent } from 'echarts/components';
import { registerTheme, use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import BaseChart from 'vue-echarts';
import { defineComponent, h } from 'vue';

use([BarChart, LineChart, RadarChart, ScatterChart,GridComponent, LegendComponent, TooltipComponent, RadarComponent, MarkLineComponent, CanvasRenderer]);

/** Tema único dos gráficos: tipografia Inter, eixos discretos, tooltip claro com sombra. */
export const CHART_THEME = 'geosafra';
const AXIS = {
    axisLine: { lineStyle: { color: '#d6d3d1' } },
    axisTick: { show: false },
    axisLabel: { color: '#78716c', fontSize: 11 },
    splitLine: { lineStyle: { color: '#f0efed', type: 'dashed' } },
    nameTextStyle: { color: '#a8a29e', fontSize: 10 },
};
registerTheme(CHART_THEME, {
    color: ['#15803d', '#2563eb', '#ea580c', '#0d9488', '#a16207', '#7c3aed', '#be123c'],
    textStyle: { fontFamily: 'Inter, ui-sans-serif, system-ui, sans-serif', color: '#44403c' },
    categoryAxis: { ...AXIS, splitLine: { show: false } },
    valueAxis: { ...AXIS, axisLine: { show: false } },
    timeAxis: { ...AXIS, splitLine: { show: false } },
    legend: { textStyle: { color: '#57534e', fontSize: 11 }, itemWidth: 14, itemHeight: 8, icon: 'roundRect' },
    tooltip: {
        backgroundColor: 'rgba(255,255,255,0.98)',
        borderColor: '#e7e5e4',
        borderWidth: 1,
        padding: [8, 12],
        textStyle: { color: '#1c1917', fontSize: 12 },
        extraCssText: 'border-radius:10px;box-shadow:0 10px 30px -10px rgba(0,0,0,.25);',
        axisPointer: { lineStyle: { color: '#a8a29e', type: 'dashed' }, crossStyle: { color: '#a8a29e' } },
    },
    line: { symbolSize: 5, lineStyle: { width: 2.5 } },
    bar: { itemStyle: { borderRadius: [4, 4, 0, 0] } },
});

/** VChart com o tema do GeoSafra já aplicado (mesmas props e atributos do vue-echarts). */
export const VChart = defineComponent({
    name: 'GsChart',
    inheritAttrs: false,
    setup(_, { attrs }) {
        return () => h(BaseChart, { theme: CHART_THEME, ...attrs });
    },
});
