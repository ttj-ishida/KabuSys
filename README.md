# KabuSys — 日本株自動売買システム

簡潔なプロジェクト概要、使い方、セットアップ手順、およびディレクトリ構成をまとめた README です。

## プロジェクト概要
KabuSys は日本株を対象とした自動売買および研究用のライブラリ兼実行フレームワークです。  
主な機能は以下の層で構成されています。

- データ層: J-Quants から株価・財務・市場カレンダー・ニュースを取得して DuckDB に保存
- 特徴量層: 研究（research）で得られた生ファクターを正規化・合成して戦略用特徴量を構築
- 戦略層: 特徴量と AI スコアを統合して売買シグナルを生成
- 実行（バックテスト）層: ポートフォリオシミュレータでシグナルを約定、バックテスト指標を算出

設計方針はルックアヘッドバイアス回避、冪等性（DB 保存は ON CONFLICT を利用）、および実運用での堅牢性（リトライ／レート制御など）に重きを置いています。

---

## 主な機能一覧
- データ取得・保存
  - J-Quants API クライアント（fetch/save: 株価、財務、カレンダー）
  - RSS ベースのニュース収集・前処理・記事→銘柄紐付け
  - DuckDB スキーマ定義と初期化（init_schema）
- 研究・特徴量
  - モメンタム／ボラティリティ／バリュー等のファクター計算（research.factor_research）
  - ファクターのクロスセクション Z スコア正規化（data.stats.zscore_normalize）
  - 特徴量構築（strategy.feature_engineering.build_features）
- シグナル生成
  - 特徴量と AI スコアを統合して final_score を算出（strategy.signal_generator.generate_signals）
  - BUY / SELL シグナルの出力（signals テーブルへ保存）
- バックテスト
  - ポートフォリオシミュレータ（手数料・スリッページ考慮）
  - 日次ループでシグナル適用、positions の書き戻し、時価評価
  - メトリクス計算（CAGR、Sharpe、Max Drawdown、勝率、Payoff Ratio）
  - CLI 実行エントリポイント（python -m kabusys.backtest.run）
- 補助
  - .env 自動ロード（プロジェクトルートの .env / .env.local。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 環境設定管理（kabusys.config.Settings）

---

## 必要要件
- Python 3.10 以上（型記法や union 演算子 | を使用）
- 依存パッケージ（例）
  - duckdb
  - defusedxml
  - そのほかプロジェクト固有に必要なライブラリ（requests 等は実装により追加）

インストール例（仮）:
```
python -m pip install duckdb defusedxml
# またはプロジェクトに合わせて pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン / ソースを用意
2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージのインストール
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクトに requirements.txt があればそれを利用してください）
4. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成すると自動で読み込まれます。
   - 必須の環境変数（kabusys.config.Settings に準拠）:
     - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注等を行う場合）
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
   - 任意 / デフォルトあり:
     - KABUS_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

   例 `.env`（簡易）:
   ```
   JQUANTS_REFRESH_TOKEN=your_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   KABUSYS_ENV=development
   ```
5. DuckDB スキーマ初期化
   Python REPL で:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
   conn.close()
   ```

---

## 使い方（代表例）

### 1) データ収集（ETL）
- J-Quants から株価を取得し DuckDB に保存する流れの一例（プログラム的に）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data import jquants_client as jq
  from kabusys.data import pipeline

  conn = init_schema("data/kabusys.duckdb")
  # 例: 当日分までの差分取得（pipeline.run_prices_etl を利用）
  res = pipeline.run_prices_etl(conn, target_date=date.today())
  print(res)
  conn.close()
  ```
- RSS ニュース収集:
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"6758","7203"})
  print(results)
  conn.close()
  ```

### 2) 特徴量構築
- features の構築（日次）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features

  conn = init_schema("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2024, 1, 31))
  print(f"features upserted: {count}")
  conn.close()
  ```

### 3) シグナル生成
- generate_signals を呼んで signals テーブルを更新:
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  n = generate_signals(conn, target_date=date(2024, 1, 31))
  print(f"signals written: {n}")
  conn.close()
  ```

### 4) バックテスト（CLI）
- 提供される CLI エントリポイント:
  ```
  python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2024-12-31 \
      --cash 10000000 --db data/kabusys.duckdb
  ```
  実行結果は標準出力にバックテストメトリクス（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）を表示します。

### 5) プログラム的にバックテストを実行
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest

conn = init_schema("data/kabusys.duckdb")
result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
print(result.metrics)
conn.close()
```

---

## 環境変数・設定（主なもの）
kabusys.config.Settings を通して参照される主要環境変数:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (development/paper_trading/live、デフォルト: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO)

自動 .env ロードはデフォルトで有効。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（概要）
（src/kabusys 以下の主要ファイルを抜粋）

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（取得・保存）
    - news_collector.py        — RSS ニュース取得・DB 保存
    - pipeline.py              — ETL パイプライン（差分取得、品質チェック）
    - schema.py                — DuckDB スキーマ定義 / init_schema
    - stats.py                 — 統計ユーティリティ（z-score 正規化等）
  - research/
    - __init__.py
    - factor_research.py       — ファクター計算（momentum/volatility/value）
    - feature_exploration.py   — 将来リターン・IC・統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py   — features 構築（正規化・フィルタ）
    - signal_generator.py      — final_score 計算・シグナル生成
  - backtest/
    - __init__.py
    - engine.py                — バックテストエンジン（run_backtest）
    - simulator.py             — ポートフォリオシミュレータ（約定モデル）
    - metrics.py               — バックテスト評価指標
    - run.py                   — CLI エントリポイント
    - clock.py                 — 模擬時計（将来拡張用）
  - execution/                  — 発注/実行層（プレースホルダ）
  - monitoring/                 — 監視・アラート関連（プレースホルダ）

---

## 開発・拡張に関するメモ
- DuckDB を使ったローカルDB設計のため、データのコピーやインメモリ DB を活用して安全にバックテスト可能（engine._build_backtest_conn）。
- API 呼び出し部分はレート制御、指数バックオフ、401 の自動リフレッシュ等の堅牢な実装方針が取られています（jquants_client）。
- テスト容易性のため、トークン注入やネットワークアクセスのモックポイントが用意されています（例: news_collector._urlopen を差し替え可能）。
- 仕様ドキュメント（StrategyModel.md / DataPlatform.md / BacktestFramework.md 等）を参照することでアルゴリズム仕様やパラメータの背景が読み取れます（ソースに参照あり）。

---

何か特定の機能（ETL 実行脚本、CI 設定、開発用の Dockerfile など）を README に追加したい場合は用途を教えてください。必要に応じてサンプル .env.example や簡易セットアップスクリプトも作成できます。