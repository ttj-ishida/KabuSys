# KabuSys

日本株向けの自動売買プラットフォームのコアライブラリ群です。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査ログなどを含むモジュール設計で、研究（research）〜本番（execution）までのワークフローを想定しています。

---

## プロジェクト概要

KabuSys は以下の主要目的を持ちます。

- J-Quants API から日本株の株価／財務／マーケットカレンダーを取得・保存する（DuckDB ベース）。
- ETL パイプラインで差分取得・保存・品質チェックを行う。
- 研究用ファクター計算（Momentum / Volatility / Value）とクロスセクション正規化を提供する。
- 戦略向けに特徴量を組成して features テーブルへ保存し、features + AI スコアを統合して売買シグナルを生成する。
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策・サイズ制限・トラッキングパラメータ除去）。
- 発注/約定/ポジションなどの監査ログ（監査テーブル群）を管理できるスキーマを提供する。

設計上の注力点（抜粋）：
- 冪等性（ON CONFLICT / トランザクション）を考慮した DB 操作
- ルックアヘッドバイアス防止（target_date 時点のデータのみ使用）
- 安全性（SSRF 対策、XML パースの安全化、API レート制御、リトライ）
- 研究と本番の分離（research モジュールは外部 API に依存しない）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レートリミット・リトライ・トークン自動リフレッシュ）
  - pipeline: 日次 ETL（市場カレンダー / 株価 / 財務）と差分取得ロジック
  - schema: DuckDB のスキーマ定義と初期化（raw / processed / feature / execution 層）
  - news_collector: RSS 取得、前処理、raw_news 保存、銘柄抽出（SSRF 防止、gzip/サイズ制限）
  - calendar_management: 営業日判定・次/前営業日取得・夜間カレンダー更新ジョブ
  - stats: クロスセクション Z スコア正規化等の統計ユーティリティ
  - features: zscore_normalize の再エクスポート
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー
- strategy/
  - feature_engineering: research の生ファクターを正規化して features テーブルへ UPSERT
  - signal_generator: features と ai_scores を統合して final_score を算出し signals テーブルに保存
- execution/: （パッケージ化のための名前空間。発注実装はここで拡張）
- monitoring/: （監視・メトリクス用の名前空間）

その他：監査ログ（audit）や ETL の品質チェック（quality モジュール）を前提とした補助機能群。

---

## セットアップ手順

1. リポジトリをクローンし、開発環境を準備します。

   ```bash
   git clone <repository-url>
   cd <repository-root>
   ```

2. Python パッケージのインストール（最小限の必要パッケージ例）。

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   # プロジェクトを編集可能モードでインストールする場合
   pip install -e .
   ```

   ※ 実際の requirements はプロジェクトに合わせて追加してください（例: slack-sdk 等、実行層に依存するライブラリ）。

3. 環境変数の設定

   ルートに `.env` を置くと自動で読み込まれます（設定は src/kabusys/config.py を参照）。

   必須環境変数（少なくとも以下は設定してください）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API を使う場合のパスワード
   - SLACK_BOT_TOKEN: Slack 通知を使う場合
   - SLACK_CHANNEL_ID: Slack 通知先チャンネルID

   オプション（デフォルト値あり）:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

   自動ロードを無効にするには:
   ```bash
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

4. DuckDB スキーマの初期化

   Python REPL またはスクリプトから init_schema を実行します。

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリ DB も可
   ```

---

## 使い方（主要ワークフロー例）

以下は代表的な使い方のサンプルコードです。実際にはロギングや例外処理を適宜追加してください。

- 日次 ETL の実行（市場カレンダー → 株価 → 財務 → 品質チェック）

  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 研究ファクターの計算（例: calc_momentum）

  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  momentums = calc_momentum(conn, date(2024, 1, 31))
  print(len(momentums), momentums[:3])
  ```

- 特徴量生成（features テーブルへの書き込み）

  ```python
  from datetime import date
  from kabusys.strategy.feature_engineering import build_features
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  n = build_features(conn, date(2024, 1, 31))
  print(f"features upserted: {n}")
  ```

- シグナル生成

  ```python
  from datetime import date
  from kabusys.strategy.signal_generator import generate_signals
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  count = generate_signals(conn, date(2024, 1, 31))
  print(f"signals written: {count}")
  ```

- ニュース収集ジョブ（RSS -> raw_news, news_symbols）

  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- J-Quants からのデータ取得（低レベル）

  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  from kabusys.config import settings

  token = get_id_token()  # settings.jquants_refresh_token を使用して取得
  recs = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

---

## 主要テーブル（概略）

プロジェクトは Raw / Processed / Feature / Execution の階層でテーブルを管理します。代表的なテーブル：

- raw_prices, raw_financials, raw_news, raw_executions
- prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- features, ai_scores
- signals, signal_queue, orders, trades, positions, portfolio_targets, portfolio_performance
- 監査系: signal_events, order_requests, executions

（詳細は src/kabusys/data/schema.py の DDL 定義を参照してください）

---

## ディレクトリ構成

（抜粋。実際のリポジトリルートはプロジェクトにより多少異なる可能性があります）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - stats.py
      - features.py
      - calendar_management.py
      - audit.py
      - audit/... (監査関連のDDL・初期化)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/  (発注・ブローカー連携を実装する場所)
    - monitoring/ (監視・メトリクス用)
- pyproject.toml / setup.cfg / README.md（本ファイル）

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須 for kabuAPI) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須 for Slack通知) — Slack bot token
- SLACK_CHANNEL_ID (必須 for Slack通知) — チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する（任意）

---

## 開発・貢献

- コーディング規約、テスト、CI の設定はプロジェクトポリシーに従ってください。
- 新しい発注ブローカーの統合や execution 層の実装は `kabusys.execution` に追加してください。
- research 側の新しいファクターは `kabusys.research` に追加し、strategy 層で利用可能にします。

---

## 注意事項・設計上のポイント

- DuckDB に対する書き込みは可能な限りトランザクションでまとめ、日付単位で DELETE→INSERT の置換を行って冪等性を維持しています。
- J-Quants クライアントは API レート（120 req/min）を守るための固定間隔スロットリングと、408/429/5xx に対する指数バックオフを実装しています。401 応答時はリフレッシュトークンを使って自動リフレッシュします。
- RSS ニュース周りは SSRF/Xml Bomb/メモリ DoS に対する防御（スキーム検証・プライベートホストチェック・gzip サイズ制限・defusedxml 利用）を実装しています。
- research と production ロジックは API 呼び出し等に依存せず、同じデータモデル（prices_daily 等）を用いて再現性のある分析が行えるように設計しています。

---

必要であれば、この README に具体的な .env.example のテンプレート、CI 用コマンド、さらなるコード利用例（cron ジョブ・Airflow スケジュール化等）を追記できます。追加で欲しいセクションやフォーマット指定があれば教えてください。