# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリ。  
DuckDB をデータストアとして用い、データ取得（J‑Quants）、ETL、ファクター計算、シグナル生成、バックテスト、ニュース収集などの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の層を持つシステム設計に基づいたライブラリです。

- Data layer（J‑Quants からの生データ取得、raw → processed → feature の ETL）
- Research layer（ファクター計算、特徴量探索）
- Strategy layer（特徴量からシグナルを生成）
- Execution / Monitoring（発注・監視のためのインターフェース）
- Backtest（戦略の擬似売買・評価）

主な設計方針：
- ルックアヘッドバイアスの回避（target_date 時点のデータのみを使用）
- DuckDB を用いたローカル DB（冪等な INSERT/UPSERT）
- API レート制御・リトライ（J‑Quants クライアント）
- ニュース収集での SSRF 防御・XML 安全パーシング

---

## 機能一覧

主要な機能（モジュール単位）:

- data.jquants_client
  - J‑Quants から日足・財務・カレンダーを取得するクライアント
  - レートリミット制御、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
- data.news_collector
  - RSS フィード取得、記事正規化、raw_news への保存、銘柄抽出（4桁コード）
  - SSRF 対策、gzip/サイズ制限、XML デフューズ処理
- data.pipeline
  - 差分取得・バックフィルを考慮した ETL ジョブ（run_prices_etl 等）
  - 品質チェックと ETL 結果集約（ETLResult）
- data.schema
  - DuckDB のスキーマ（raw / processed / feature / execution）定義と初期化（init_schema）
- data.stats
  - zscore_normalize（クロスセクション Z スコア正規化）
- research.factor_research / feature_exploration
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリー
- strategy.feature_engineering
  - research で計算した raw factor をユニバースフィルタ・正規化して features テーブルへ保存
- strategy.signal_generator
  - features と ai_scores を統合し final_score を算出して BUY/SELL シグナルを signals テーブルへ保存
  - Bear レジーム抑制、エグジット条件（ストップロス等）
- backtest
  - run_backtest: 本番 DB から必要なデータをコピーして日次の擬似約定ループを回す
  - PortfolioSimulator: スリッページ/手数料を反映した約定シミュレータ
  - metrics: CAGR / Sharpe / MaxDD / 勝率等の算出
  - CLI エントリポイント: python -m kabusys.backtest.run

---

## セットアップ手順

前提:
- Python 3.9+（本コードは typing の新機能・annotations を使用）
- Git

1. リポジトリをクローン
   ```
   git clone <this-repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール  
   最低限必要なパッケージ:
   - duckdb
   - defusedxml
   - （標準ライブラリのみで実装している箇所が多いため外部依存は最小限です）

   例:
   ```
   pip install duckdb defusedxml
   ```

   ※ 実運用ではロギングやテスト用のパッケージ等を追加してください。requirements.txt がある場合は `pip install -r requirements.txt` を使用します。

4. 環境変数の設定  
   プロジェクトルート（.git または pyproject.toml のある場所）に `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   必須の環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabu ステーション API 用パスワード（execution 層利用時）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（監視機能利用時）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネルID

   任意／デフォルト:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN="xxxxx"
   KABU_API_PASSWORD="pwd"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C0123456"
   DUCKDB_PATH="data/kabusys.duckdb"
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DB スキーマ初期化
   Python REPL やスクリプトから:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイル DB を作成／初期化
   conn.close()
   ```

---

## 使い方

ここでは代表的なワークフローと実行例を示します。

1) DuckDB の初期化（上で説明した通り）
   ```bash
   python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   ```

2) J‑Quants からデータ取得・保存（プログラムから）
   ```python
   import duckdb
   from datetime import date
   from kabusys.data import jquants_client as jq
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   # 全銘柄の日足を日付範囲で取得
   recs = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
   saved = jq.save_daily_quotes(conn, recs)
   print("saved:", saved)
   conn.close()
   ```

3) ニュース収集・保存（RSS）
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   conn = init_schema("data/kabusys.duckdb")
   # known_codes に有効なコード集合を渡すと銘柄紐付けまで実施
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={'7203','6758'})
   print(results)
   conn.close()
   ```

4) 特徴量構築（features テーブルへの書き込み）
   ```python
   import duckdb
   from datetime import date
   from kabusys.strategy import build_features

   conn = duckdb.connect("data/kabusys.duckdb")
   count = build_features(conn, target_date=date(2024,1,10))
   print("features upserted:", count)
   conn.close()
   ```

5) シグナル生成
   ```python
   from kabusys.strategy import generate_signals
   import duckdb
   from datetime import date

   conn = duckdb.connect("data/kabusys.duckdb")
   total = generate_signals(conn, target_date=date(2024,1,10))
   print("signals:", total)
   conn.close()
   ```

6) バックテスト（CLI）
   DuckDB に prices_daily, features, ai_scores, market_regime, market_calendar 等が用意されている前提で実行します。
   ```
   python -m kabusys.backtest.run \
     --start 2023-01-01 --end 2024-12-31 \
     --cash 10000000 --db data/kabusys.duckdb
   ```
   実行後、CAGR / Sharpe / Max Drawdown / 勝率 などが出力されます。

7) バックテストを Python API から呼ぶ
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.schema import init_schema
   from kabusys.backtest.engine import run_backtest

   conn = init_schema("data/kabusys.duckdb")
   res = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
   print(res.metrics)
   conn.close()
   ```

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN: 必須（J‑Quants認証用）
- KABU_API_PASSWORD: 必須（kabu API 連携時）
- SLACK_BOT_TOKEN: 必須（Slack 通知を使う場合）
- SLACK_CHANNEL_ID: 必須（Slack 通知を使う場合）
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると自動で .env をロードしない

---

## ディレクトリ構成

主要ファイル・ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - pipeline.py
    - schema.py
    - stats.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - backtest/
    - __init__.py
    - engine.py
    - simulator.py
    - metrics.py
    - run.py  — CLI entrypoint
    - clock.py
  - execution/  — 発注関連モジュール（起点ファイルあり）
  - (monitoring) — 監視関連モジュール（__all__ に含めているが実装は別途）

README 向けのツリー（簡易）:
```
src/kabusys/
├─ config.py
├─ data/
│  ├─ jquants_client.py
│  ├─ news_collector.py
│  ├─ pipeline.py
│  ├─ schema.py
│  └─ stats.py
├─ research/
│  ├─ factor_research.py
│  └─ feature_exploration.py
├─ strategy/
│  ├─ feature_engineering.py
│  └─ signal_generator.py
├─ backtest/
│  ├─ engine.py
│  ├─ simulator.py
│  ├─ metrics.py
│  └─ run.py
└─ execution/
```

---

## 開発／運用上の注意点

- DuckDB のファイルはプロジェクト外（data/ 以下など）に保存することを推奨します。init_schema は parent ディレクトリを自動作成します。
- J‑Quants API はレート制限（120 req/min）が設定されています。jquants_client は固定間隔の RateLimiter を実装していますが、大量リクエスト時は更なる調整が必要です。
- ニュース収集では外部フィードのサイズや圧縮、リダイレクト先の検証を行います。SSRF 対策や XML デフューズに留意していますが、実運用でも入力ソースの管理を行ってください。
- バックテストでは実データのコピーを作成して実行するため、本番データの汚染は発生しません。ただしコピー元 DB の整備（必要テーブルの作成／データ整備）は事前に行ってください。
- 環境設定は .env/.env.local で管理できます。CI やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使い手動で環境変数を注入してください。

---

必要であれば、README にサンプル .env.example、より詳細な ETL 実行手順（run_prices_etl / run_financials_etl の使い方）や API ドキュメント（各関数の引数・戻り値サンプル）を追加します。どの部分の詳細が欲しいか教えてください。