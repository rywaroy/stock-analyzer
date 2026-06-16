module.exports = {
  apps: [
    {
      name: "stock-analyzer",
      script: "./server/index.js",
      // 生产环境
      env_production: {
        NODE_ENV: "production",
        PORT: 8001,
        MYSQL_HOST: "127.0.0.1",
        MYSQL_PORT: 3306,
        MYSQL_USER: "zzh",
        MYSQL_PASSWORD: "JCdt3[YhD=y)*9",
        MYSQL_DATABASE: "stock_analysis_test",
        INGEST_API_TOKEN: "stock-analysis-ingest-2026-6f8c2d91b7a443e0",
      },
    },
  ],
};
