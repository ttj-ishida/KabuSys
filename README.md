# KabuSys

KabuSys は日本株向けの研究・データパイプライン、戦略・ポートフォリオ構築、バックテスト、ニュース収集までを含む自動売買システムのコアライブラリです。本リポジトリは、DuckDB をデータストアに使う研究／バックテスト中心の実装を含んでいます。

---

## プロジェクト概要

主な目的は以下です。

- J-Quants 等からマーケットデータ・財務データを取得して DuckDB に保存する ETL。
- 研究（factor 計算、特徴量正規化、探索解析）。
- 戦略（特徴量→スコア→BUY/SELL シグナル生成）。
- ポートフォリオ構築（候補選定、配分計算、リスク調整、ポジションサイジング）。
- バックテスト（疑似約定、手数料／スリッページモデル、メトリクス算出）。
- ニュース収集（RSS 取得、記事保存、銘柄抽出） — look-ahead bias を考慮したデザイン。

設計方針として、可能な箇所は DB 参照を限定し、ルックアヘッドを防ぐため「target_date 時点で利用可能なデータのみを使う」ことを重視しています。

---

## 主な機能一覧

- data/
  - J-Quants API クライアント（認証、ページネーション、レート制御、リトライ、DuckDB への保存）
  - ニュース収集（RSS 取得、SSRF 対策、テキスト前処理、記事保存、銘柄抽出）
- research/
  - factor 計算（モメンタム、ボラティリティ、バリュー等）
  - feature 探索（IC、将来リターン計算、統計サマリ）
- strategy/
  - 特徴量ビルド（正規化・クリップ・features テーブル保存）
  - シグナル生成（final_score 計算、Bear レジーム抑制、SELL/BUY の判定と signals テーブル書込）
- portfolio/
  - 候補選定、等配分・スコア加重配分、リスク調整（セクター上限、レジーム乗数）、ポジションサイジング
- backtest/
  - バックテストエンジン（データのインメモリコピー、日次ループ、擬似約定）
  - ポートフォリオシミュレータ（部分約定、手数料／スリッページ反映）
  - メトリクス計算（CAGR、Sharpe、MaxDD、勝率、Payoff 等）
  - CLI 実行スクリプト（python -m kabusys.backtest.run）
- monitoring / execution （骨格・参照用モジュール群）

---

## セットアップ手順

前提
- Python 3.10 以上（Union 型表記 `X | Y` を使用）。
- Git が使える環境。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージのインストール（最低限推奨）
   ```
   pip install duckdb defusedxml
   ```
   ※ packaging（pip install -e .）や requirements.txt がある場合はそちらを使ってください。

4. プロジェクトを editable install する（あれば）
   ```
   pip install -e .
   ```

5. 環境変数の設定
   - プロジェクトルートに `.env`（や `.env.local`）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API パスワード（自動売買連携時）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - オプション（デフォルトあり）:
     - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL — DEBUG|INFO|...（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要ワークフロー）

以下は代表的なワークフローと実行方法です。

1. データ収集（J-Quants）
   - J-Quants から日足や財務データを取得:
     ```python
     from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token

     id_token = get_id_token()  # settings.jquants_refresh_token を利用
     records = fetch_daily_quotes(id_token=id_token, date_from=..., date_to=...)
     conn = init_schema("path/to/kabusys.duckdb")  # data.schema の init_schema を使う想定
     save_daily_quotes(conn, records)
     conn.close()
     ```
   - 市場カレンダー、銘柄リスト、財務データも同様に fetch_* / save_* を使用。

2. ニュース収集
   ```python
   from kabusys.data.news_collector import run_news_collection

   conn = init_schema("path/to/kabusys.duckdb")
   known_codes = set(...)  # stocks テーブル等から取得した有効コード集合
   results = run_news_collection(conn, known_codes=known_codes)
   conn.close()
   ```

3. 特徴量計算（features テーブル作成）
   ```python
   from datetime import date
   import duckdb
   from kabusys.strategy.feature_engineering import build_features

   conn = duckdb.connect("path/to/kabusys.duckdb")
   count = build_features(conn, target_date=date(2024, 1, 31))
   conn.close()
   ```

4. シグナル生成（signals テーブルへ書込）
   ```python
   from kabusys.strategy.signal_generator import generate_signals

   conn = duckdb.connect("path/to/kabusys.duckdb")
   n = generate_signals(conn, target_date=date(2024, 1, 31))
   conn.close()
   ```

5. バックテスト（CLI）
   - CLI で簡単にバックテスト実行:
     ```
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2024-12-31 \
       --cash 10000000 \
       --db path/to/kabusys.duckdb
     ```
   - 主要オプション:
     - --allocation-method: equal | score | risk_based（デフォルト: risk_based）
     - --slippage / --commission / --max-position-pct / --max-utilization / --max-positions / --lot-size など

6. ライブラリとしての利用
   - 各モジュールは関数ベースで分かれており、パイプラインの一部のみを呼び出して組み合わせ可能です（例：研究→特徴量→信号→サイジング→約定シミュレーション）。

---

## 設定と自動 .env ロード

- kabusys.config モジュールはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、.env / .env.local を自動で読み込みます。
- 読み込み優先順: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- 必須の環境変数が不足すると Settings プロパティで ValueError を送出します。

---

## 主要 CLI / スクリプト

- バックテスト実行: python -m kabusys.backtest.run
- （将来的に）収集ジョブや ETL 用のスクリプトを追加することが想定されています。

---

## ディレクトリ構成（抜粋）

以下は主要モジュールと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義、version
  - config.py — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
  - data/
    - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存関数）
    - news_collector.py — RSS 収集・記事保存・銘柄抽出
    - (その他 data/*.py: schema, calendar_management などを想定)
  - research/
    - factor_research.py — momentum / volatility / value 計算
    - feature_exploration.py — forward returns / IC / summary
  - strategy/
    - feature_engineering.py — features テーブル作成（正規化・UPSERT）
    - signal_generator.py — final_score 計算 → signals 書込
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・aggregate cap・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - backtest/
    - engine.py — バックテストループ（run_backtest）
    - simulator.py — PortfolioSimulator（擬似約定、history/trades 管理）
    - metrics.py — バックテストメトリクス計算
    - run.py — CLI エントリポイント
    - clock.py — SimulatedClock（将来拡張用）
  - portfolio/, execution/, monitoring/ — 実運用・監視・発注レイヤの骨格

---

## 注意点 / 既知の設計上の挙動

- look-ahead bias 防止のため、戦略と特徴量生成は target_date 時点で知られているデータのみを使用するように設計されています。バックテストでは start_date より前のデータをコピーする処理を経由します。
- news_collector は SSRF 対策、gzip サイズチェック、XML パース保護（defusedxml）などセキュリティ対策を組み込んでいます。
- J-Quants クライアントはレート制限（120 req/min）を固定間隔スロットリングで守ります。401 を受けた際はリフレッシュトークンによる再取得を試みます。
- DuckDB のスキーマ初期化関数（init_schema）は data.schema 側で提供されている想定です。バックテストの CLI もこの init_schema を利用して接続します。

---

## 貢献 / 開発メモ

- 新しい機能を追加する際は、ルックアヘッドバイアスを導入しない設計に注意してください（target_date のみ使用）。
- DB に対する書き込みは可能な限り日付単位で置換（DELETE → INSERT のトランザクション）して冪等性を担保しています。
- 単体テストは DuckDB のインメモリモードを使うと容易に構築できます（init_schema(":memory:") 想定）。

---

必要であれば、README に以下を追加できます。
- 具体的な依存パッケージ一覧（requirements.txt を基に）
- DB スキーマの説明 / SQL DDL（data/schema.py の内容に基づく）
- 具体的なデータ収集 / ETL の実行例（cron や Airflow での運用例）
- 実運用時の kabu ステーション連携方法（execution 層の実装がある場合）

ほかに追記したい項目があれば教えてください。