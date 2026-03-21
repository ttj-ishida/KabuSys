# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、DB スキーマ、特徴量計算、シグナル生成、ニュース収集、監査ログ等を含むモジュール化された実装を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買基盤を構築するための内部ライブラリ群です。主な目的は以下です。

- J-Quants API から株価・財務・カレンダーを取得して DuckDB に保持する（差分更新／冪等保存）
- 研究で計算した生ファクターを正規化・合成して特徴量テーブルを作成
- 特徴量 + AI スコアを統合して売買シグナルを生成
- RSS フィードからニュースを収集し、記事と銘柄の紐付けを行う
- 発注／約定／ポジション等の監査ログ構造を提供
- カレンダーや品質チェック等のユーティリティを備える

設計方針としては「ルックアヘッドバイアスの排除」「冪等性」「ネットワーク／セキュリティ対策（SSRF 等）」「テストしやすさ」を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レートリミット・リトライ・トークン自動リフレッシュ対応）
  - pipeline: 日次 ETL（差分更新、バックフィル、品質チェック）
  - schema: DuckDB スキーマ定義および初期化
  - news_collector: RSS 収集・前処理・DB 保存・銘柄抽出
  - calendar_management: 市場カレンダー管理（営業日判定、next/prev など）
  - stats: Z スコア正規化など汎用統計ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value ファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、ファクターサマリ
- strategy/
  - feature_engineering: 生ファクターを正規化し `features` テーブルへ保存
  - signal_generator: features と ai_scores を統合して BUY/SELL シグナルを生成（冪等）
- execution / monitoring: 発注・監視周りのモジュール用プレースホルダ（パッケージ構造に準備済み）
- config: 環境変数管理（.env 自動読み込み・必須チェック）

主な設計仕様はコード内の docstring（StrategyModel.md, DataPlatform.md など参照）に準拠しています。

---

## セットアップ手順

前提: Python 3.10+（型注釈に Union | を使用）、DuckDB が必要です。

1. リポジトリをクローン／チェックアウト

   git clone <repo-url>
   cd <repo-root>

2. Python 仮想環境を作成・有効化（任意だが推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要なパッケージをインストール

   pip install -U pip
   pip install duckdb defusedxml

   （将来的には requirements.txt / pyproject.toml を備えて pip install -e . で管理することを想定）

4. 環境変数を設定

   ルートに `.env`（および開発環境用に `.env.local`）を作成すると自動的にロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   必要な環境変数（主なもの）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD     : kabu API パスワード（必須）
   - KABU_API_BASE_URL     : kabu API ベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN       : Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID      : 通知先 Slack チャンネル ID（必須）
   - DUCKDB_PATH           : DuckDB ファイルパス（省略可、デフォルト data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 SQLite パス（省略可、デフォルト data/monitoring.db）
   - KABUSYS_ENV           : 実行環境 (development / paper_trading / live)（省略可、デフォルト development）
   - LOG_LEVEL             : ログレベル (DEBUG/INFO/...)（省略可）

   例 (.env):
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb

5. DuckDB スキーマ初期化

   Python REPL やスクリプトで以下を実行して DB とテーブルを作成します。

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

   init_schema は親ディレクトリがなければ自動的に作成します。":memory:" を渡すとインメモリ DB になります。

---

## 使い方（主要フローの例）

以下は主要な利用例（Python スクリプト／REPL で実行）です。すべて DuckDB 接続を渡して呼び出します。

1. スキーマ初期化（先述）

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

2. 日次 ETL（J-Quants から差分取得して保存・品質チェック）

   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # target_date を指定しなければ今日

   ETLResult オブジェクトに取得数・保存数・品質問題・エラー情報が含まれます。

3. 特徴量の構築（research の生ファクターを集約して features テーブルへ保存）

   from kabusys.strategy import build_features
   from datetime import date
   n = build_features(conn, date(2024, 1, 10))  # target_date を指定

   戻り値は upsert した銘柄数です。

4. シグナル生成

   from kabusys.strategy import generate_signals
   from datetime import date
   total = generate_signals(conn, date(2024, 1, 10))
   # threshold / weights を引数で調整可能

   BUY と SELL を signals テーブルへ日付単位で置換（冪等）します。

5. ニュース収集（RSS）

   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})

   新規保存件数などを返します。URL 正規化／SSRF 防止／サイズ制限などの安全対策を実装しています。

6. カレンダー操作（営業日判定、次営業日取得など）

   from kabusys.data.calendar_management import is_trading_day, next_trading_day
   from datetime import date
   is_trading = is_trading_day(conn, date(2024, 1, 10))
   next_day = next_trading_day(conn, date(2024, 1, 10))

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabu ステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack 通知の Bot トークン
- SLACK_CHANNEL_ID (必須): 通知先チャネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB の SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development|paper_trading|live)
- LOG_LEVEL: ログレベル (DEBUG/INFO/...)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化できます（テスト用途など）

設定は .env / .env.local から自動で読み込まれます（プロジェクトルートは .git または pyproject.toml を基準に探索）。

---

## トラブルシューティング・注意点

- 必須環境変数が未設定だと Settings プロパティで ValueError が発生します。README の「環境変数（主要）」を参照して設定してください。
- init_schema() が DB ファイルの親ディレクトリを自動作成しますが、パーミッションに注意してください。
- J-Quants API 呼び出しはレート制限（120 req/min）を考慮した実装があります。大量取得時は処理時間に余裕を持ってください。
- news_collector は外部ネットワークにアクセスします。社内ネットワーク内で実行する場合、SSRF ブロック機能が適切に働くよう DNS 解決などが必要です。
- features / signals の生成は「ルックアヘッドバイアス」を防ぐ設計になっています。target_date 時点のデータのみを使用する点に注意してください。
- DuckDB のバージョンによっては外部キーや ON DELETE 差異があります。スキーマ注釈を読んで運用ルールに従ってください。

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - stats.py
      - pipeline.py
      - features.py
      - calendar_management.py
      - audit.py
      - audit の DDL 等（監査用）
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/  (パッケージ空ディレクトリ/将来の発注実装)
    - monitoring/ (監視ロジック用プレースホルダ)

各モジュールは docstring に詳細な仕様（処理フロー・設計方針・SQL や数式）を含んでおり、利用者はそれらに従って呼び出せます。

---

## 開発メモ・拡張ポイント

- strategy の重みや閾値は generate_signals の引数で上書き可能です。運用時は A/B テストやウォークフォワード検証を行ってからパラメータを固定してください。
- execution 層（ブローカ API 呼び出し）と監査ログの連携は実装予定／拡張可能です。order_requests → executions のワークフローを追加してください。
- AI スコア（ai_scores テーブル）の生成は外部プロセスで行い、同日付でテーブルに投入する想定です。signal_generator は ai_scores が存在しない場合も中立値で補完します。
- 品質チェック（quality モジュール）は pipeline.run_daily_etl 内で呼ばれます。重大度を検知したときの運用フロー（アラート／手動調査）を整備してください。

---

必要であれば README を英語版にしたり、サンプルスクリプト（ETL ジョブ、日次バッチ、Dockerfile、systemd ユニット等）を追加で作成します。どのサンプルが欲しいか教えてください。