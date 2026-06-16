import DefaultTheme from 'vitepress/theme';
import type { Theme } from 'vitepress';
import Antd from 'ant-design-vue';
import 'ant-design-vue/dist/reset.css';
import StockDashboard from './components/StockDashboard.vue';
import StockDetail from './components/StockDetail.vue';
import './styles.css';

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.use(Antd);
    app.component('StockDashboard', StockDashboard);
    app.component('StockDetail', StockDetail);
  },
} satisfies Theme;
