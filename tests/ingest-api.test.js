import assert from 'node:assert/strict';
import { once } from 'node:events';
import http from 'node:http';
import test from 'node:test';

import { createApp, shouldStartServer } from '../server/index.js';

const DEFAULT_TOKEN = 'stock-analysis-ingest-2026-6f8c2d91b7a443e0';

test('shouldStartServer starts when running under PM2', () => {
  assert.equal(shouldStartServer(['node', '/pm2/ProcessContainerFork.js'], { pm_id: '13' }), true);
});

test('shouldStartServer does not start when imported by tests', () => {
  assert.equal(shouldStartServer(['node', '/tmp/tests/ingest-api.test.js'], {}), false);
});

function createFakePool() {
  return {
    async query() {
      return [[{ ok: 1 }]];
    },
  };
}

function sampleResult() {
  return {
    code: '002466',
    name: '天齐锂业',
    score: 5,
    signal: '观望',
    confidence: '低',
    regime: 'range',
    advice: '接近中性，当前更适合观察。',
    horizon_scores: {
      short_term: { label: '短期', score: -8, signal: '观望' },
      medium_term: { label: '中期', score: 6, signal: '观望' },
      long_term: { label: '长期', score: 18, signal: '买入偏向' },
    },
    parts: [{ module: '长期趋势', points: 4, reason: '测试' }],
    source_errors: [],
    raw: {
      code: '002466',
      name: '天齐锂业',
      industry: '能源金属',
      listed_at: '2010-08-31',
      report_date: '2026-03-31',
      overview: { 总股本: 1641221583, 流通股: 1470000000 },
      technical: {
        trade_date: '2026-06-12',
        latest_close: 62.5,
        latest_volume: 990333.98,
        latest_amount: 6140893986,
        turnover_rate: 6.71,
        avg_volume_5: 787629.08,
        avg_volume_20: 610290.05,
        volume_ratio_5: 1.257,
        macd: { dif: -2.12, dea: -1.93, bar: -0.39 },
        boll: { mid: 63.17, upper: 70.05, lower: 56.29, position: '中轨下方' },
        kdj: { k: 57.32, d: 37.2, j: 97.58 },
        rsi: { rsi6: 57.77, rsi12: 47.36, rsi24: 48.21 },
      },
      technical_trend: {
        rating: '技术趋势震荡',
        score: 1,
        conclusion: '趋势震荡。',
        signals: ['测试长期趋势'],
        windows: [
          {
            days: 20,
            return_pct: -9.56,
            close_vs_ma_pct: -1.06,
            macd_positive_ratio: 0,
            boll_mid_above_ratio: 0,
            rsi24: 48.21,
            volume_ratio_20: 1.62,
          },
        ],
      },
      metrics: [{ label: 'ROE', value: 4.31 }],
      strengths: [],
      risks: [],
    },
  };
}

function sampleAiEtf() {
  return {
    portfolioName: 'AI_RECOMMENDED_ETF',
    tradeDate: '2026-06-12',
    adjustType: 'qfq',
    selectionRule: '首次生成，10 只股票等权配置。',
    nav: 1000000,
    dailyReturnPct: 0,
    cumulativeReturnPct: 0,
    realizedPnl: 0,
    unrealizedPnl: 0,
    totalPnl: 0,
    turnoverPct: 100,
    holdings: [
      {
        stockCode: '002466',
        stockName: '天齐锂业',
        industry: '能源金属',
        previousWeightPct: 0,
        targetWeightPct: 10,
        weightDeltaPct: 10,
        action: 'buy',
        referencePrice: 62.5,
        simulatedQuantity: 1600,
        simulatedNotional: 100000,
        score: 5,
        shortTermScore: -8,
        mediumTermScore: 6,
        longTermScore: 18,
        signalLabel: '观望',
        shortTermSignalLabel: '观望',
        mediumTermSignalLabel: '观望',
        longTermSignalLabel: '买入偏向',
        confidence: '低',
        rationale: '测试选择理由',
        risks: ['测试风险'],
      },
    ],
    rebalance: [
      {
        stockCode: '002466',
        stockName: '天齐锂业',
        action: 'buy',
        previousWeightPct: 0,
        targetWeightPct: 10,
        weightDeltaPct: 10,
        referencePrice: 62.5,
        simulatedQuantityDelta: 1600,
        simulatedNotionalDelta: 100000,
        realizedPnl: 0,
        realizedReturnPct: 0,
        reason: '新纳入组合',
      },
    ],
  };
}

function createRecordingPool() {
  const calls = [];
  const connection = {
    calls,
    async beginTransaction() {
      calls.push({ type: 'begin' });
    },
    async query(sql, params = []) {
      calls.push({ type: 'query', sql, params });
      if (sql.includes('FROM stock_signal_outcome') && sql.includes('GROUP BY stock_code')) {
        return [
          [
            {
              stock_code: '002466',
              horizon: 'short_term',
              window_days: 5,
              sample_count: 12,
              directional_count: 10,
              hit_rate_pct: 60,
              avg_return_pct: 1.25,
              avg_max_drawdown_pct: -2.1,
              avg_max_runup_pct: 4.2,
            },
          ],
        ];
      }
      if (sql.includes('FROM stock_ai_etf_snapshot')) {
        return [
          [
            {
              portfolioName: 'AI_RECOMMENDED_ETF',
              tradeDate: '2026-06-12',
              adjustType: 'qfq',
              selectionRule: '首次生成，10 只股票等权配置。',
              nav: 1000000,
              dailyReturnPct: 0,
              cumulativeReturnPct: 0,
              realizedPnl: 0,
              unrealizedPnl: 0,
              totalPnl: 0,
              turnoverPct: 100,
              holdingCount: 1,
              summary_json: JSON.stringify({ note: '测试' }),
              updatedAt: '2026-06-12 18:00:00',
            },
          ],
        ];
      }
      if (sql.includes('FROM stock_ai_etf_holding')) {
        return [
          [
            {
              portfolioName: 'AI_RECOMMENDED_ETF',
              tradeDate: '2026-06-12',
              stockCode: '002466',
              stockName: '天齐锂业',
              industry: '能源金属',
              previousWeightPct: 0,
              targetWeightPct: 10,
              weightDeltaPct: 10,
              action: 'buy',
              referencePrice: 62.5,
              simulatedQuantity: 1600,
              simulatedNotional: 100000,
              score: 5,
              shortTermScore: -8,
              mediumTermScore: 6,
              longTermScore: 18,
              confidence: '低',
              rationale: '测试选择理由',
              risks_json: JSON.stringify(['测试风险']),
            },
          ],
        ];
      }
      if (sql.includes('FROM stock_ai_etf_trade')) {
        return [
          [
            {
              portfolioName: 'AI_RECOMMENDED_ETF',
              tradeDate: '2026-06-12',
              stockCode: '002466',
              stockName: '天齐锂业',
              action: 'buy',
              previousWeightPct: 0,
              targetWeightPct: 10,
              weightDeltaPct: 10,
              referencePrice: 62.5,
              simulatedQuantityDelta: 1600,
              simulatedNotionalDelta: 100000,
              realizedPnl: 0,
              realizedReturnPct: 0,
              reason: '新纳入组合',
            },
          ],
        ];
      }
      return [[]];
    },
    async commit() {
      calls.push({ type: 'commit' });
    },
    async rollback() {
      calls.push({ type: 'rollback' });
    },
    release() {
      calls.push({ type: 'release' });
    },
  };
  return {
    calls,
    async getConnection() {
      calls.push({ type: 'getConnection' });
      return connection;
    },
    async query(sql, params = []) {
      if (sql === 'SELECT 1 AS ok') {
        return [[{ ok: 1 }]];
      }
      return connection.query(sql, params);
    },
  };
}

async function postJson(server, path, body, headers = {}) {
  const address = server.address();
  const response = await fetch(`http://127.0.0.1:${address.port}${path}`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      ...headers,
    },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(1000),
  });
  return {
    status: response.status,
    body: await response.json(),
  };
}

async function withServer(app, run) {
  const server = http.createServer(app);
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  try {
    await run(server);
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
}

test('POST /api/ingest/daily-analysis rejects missing bearer token', async () => {
  const app = createApp({ pool: createFakePool(), ingestToken: 'secret' });

  await withServer(app, async (server) => {
    const response = await postJson(server, '/api/ingest/daily-analysis', { adjustType: 'qfq', results: [] });

    assert.equal(response.status, 401);
    assert.equal(response.body.error, '上报接口未授权');
  });
});

test('POST /api/ingest/daily-analysis rejects wrong bearer token', async () => {
  const app = createApp({ pool: createFakePool(), ingestToken: 'secret' });

  await withServer(app, async (server) => {
    const response = await postJson(
      server,
      '/api/ingest/daily-analysis',
      { adjustType: 'qfq', results: [] },
      { authorization: 'Bearer wrong' },
    );

    assert.equal(response.status, 401);
    assert.equal(response.body.error, '上报接口未授权');
  });
});

test('POST /api/ingest/daily-analysis accepts the built-in default token', async () => {
  const app = createApp({ pool: createRecordingPool(), projectRootPath: '/tmp/no-static-dist' });

  await withServer(app, async (server) => {
    const response = await postJson(
      server,
      '/api/ingest/daily-analysis',
      { adjustType: 'qfq', results: [sampleResult()] },
      { authorization: `Bearer ${DEFAULT_TOKEN}` },
    );

    assert.equal(response.status, 200);
    assert.equal(response.body.persistedCount, 1);
  });
});

test('POST /api/ingest/daily-analysis returns 400 for invalid adjustType', async () => {
  const app = createApp({ pool: createFakePool(), projectRootPath: '/tmp/no-static-dist' });

  await withServer(app, async (server) => {
    const response = await postJson(
      server,
      '/api/ingest/daily-analysis',
      { adjustType: 'bad', results: [] },
      { authorization: `Bearer ${DEFAULT_TOKEN}` },
    );

    assert.equal(response.status, 400);
    assert.equal(response.body.error, 'adjustType 只支持 none/qfq/hfq');
  });
});

test('POST /api/ingest/daily-analysis persists results and refreshes reports in one transaction', async () => {
  const pool = createRecordingPool();
  const app = createApp({ pool, ingestToken: 'secret', projectRootPath: '/tmp/no-static-dist' });

  await withServer(app, async (server) => {
    const response = await postJson(
      server,
      '/api/ingest/daily-analysis',
      { adjustType: 'qfq', results: [sampleResult()] },
      { authorization: 'Bearer secret' },
    );

    assert.equal(response.status, 200);
    assert.equal(response.body.persistedCount, 1);
    assert.deepEqual(response.body.items, [
      { stockCode: '002466', tradeDate: '2026-06-12', score: 5, signal: '观望', confidence: '低' },
    ]);
  });

  const sqlText = pool.calls.filter((call) => call.type === 'query').map((call) => call.sql).join('\n');
  assert.equal(pool.calls[0].type, 'getConnection');
  assert.equal(pool.calls.some((call) => call.type === 'begin'), true);
  assert.equal(pool.calls.some((call) => call.type === 'commit'), true);
  assert.equal(pool.calls.some((call) => call.type === 'rollback'), false);
  assert.match(sqlText, /INSERT INTO stock_security/);
  assert.match(sqlText, /INSERT INTO stock_daily_quote/);
  assert.match(sqlText, /INSERT INTO stock_daily_signal_score/);
  assert.match(sqlText, /INSERT INTO stock_signal_outcome/);
  assert.match(sqlText, /UPDATE stock_signal_outcome outcome/);
  assert.match(sqlText, /INSERT INTO stock_daily_report/);
  assert.equal(
    pool.calls.some((call) => call.type === 'query' && call.params.some((param) => String(param).includes('## 历史验证'))),
    true,
  );
});

test('POST /api/ingest/daily-analysis persists optional AI ETF payload', async () => {
  const pool = createRecordingPool();
  const app = createApp({ pool, ingestToken: 'secret', projectRootPath: '/tmp/no-static-dist' });

  await withServer(app, async (server) => {
    const response = await postJson(
      server,
      '/api/ingest/daily-analysis',
      { adjustType: 'qfq', results: [sampleResult()], aiEtf: sampleAiEtf() },
      { authorization: 'Bearer secret' },
    );

    assert.equal(response.status, 200);
    assert.equal(response.body.aiEtf?.portfolioName, 'AI_RECOMMENDED_ETF');
    assert.equal(response.body.aiEtf?.holdingCount, 1);
  });

  const sqlText = pool.calls.filter((call) => call.type === 'query').map((call) => call.sql).join('\n');
  assert.match(sqlText, /INSERT INTO stock_ai_etf_snapshot/);
  assert.match(sqlText, /INSERT INTO stock_ai_etf_holding/);
  assert.match(sqlText, /INSERT INTO stock_ai_etf_trade/);
});

test('GET /api/ai-etf returns latest portfolio snapshot with holdings and rebalance', async () => {
  const app = createApp({ pool: createRecordingPool(), projectRootPath: '/tmp/no-static-dist' });

  await withServer(app, async (server) => {
    const address = server.address();
    const response = await fetch(`http://127.0.0.1:${address.port}/api/ai-etf`, {
      signal: AbortSignal.timeout(1000),
    });
    const body = await response.json();

    assert.equal(response.status, 200);
    assert.equal(body.snapshot.portfolioName, 'AI_RECOMMENDED_ETF');
    assert.equal(body.holdings[0].action, 'buy');
    assert.equal(body.rebalance[0].action, 'buy');
  });
});
