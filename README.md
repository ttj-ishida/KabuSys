# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
データ収集（J-Quants）、DuckDB への保存、特徴量計算、戦略シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は上場日本株の自動売買システム向けに設計された Python モジュール群です。主な目的は以下：

- J-Quants API からの差分データ取得（株価、財務、カレンダー）
- DuckDB を用いたデータレイヤ（raw / processed / feature / execution）の永続化
- 研究用ファクター計算（Momentum、Volatility、Value 等）と Z スコア正規化
- 戦略シグナルの生成（BUY / SELL）およびエグジット判定
- RSS ベースのニュース収集と銘柄抽出
- マーケットカレンダー管理、監査ログ（発注〜約定のトレース）

設計上の特徴：

- ルックアヘッドバイアスを避ける設計（target_date 時点のデータのみ使用）
- DuckDB を主体とした冪等保存（ON CONFLICT を利用）
- 外部 API 呼び出しのリトライ、トークン自動リフレッシュ、レート制御を実装
- 標準ライブラリ中心で依存を最小化

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション、リトライ、レート制御、トークン管理）
  - schema: DuckDB スキーマ定義 & 初期化（raw/processed/feature/execution レイヤ）
  - pipeline: 日次 ETL（差分取得、バックフィル、品質チェック統合）
  - news_collector: RSS 取得・前処理・DB 保存・銘柄抽出
  - calendar_management: JPX カレンダー管理・営業日ロジック
  - stats: Z スコア正規化などの統計ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value のファクター計算
  - feature_exploration: 将来リターン計算・IC（Information Coefficient）・統計サマリー
- strategy/
  - feature_engineering: ファクター統合・ユニバースフィルタ・正規化 → features テーブル保存
  - signal_generator: features + ai_scores を統合して BUY/SELL シグナルを生成し signals テーブルへ保存
- execution/
  - （発注・注文管理のためのテーブル設計やラッパーを想定）
- config.py
  - 環境変数管理、.env 自動読み込み（プロジェクトルート基準）、必須設定チェック

---

## セットアップ手順

> 要件: Python 3.10 以上（typing の新しい注釈表記を使用しています）

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. 依存ライブラリをインストール
   - 最低限必要なパッケージ:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があればそれを使用して下さい。パッケージとしてインストールする場合は pip install -e . を利用できます。）

4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動的に読み込まれます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注連携を使う場合）
     - SLACK_BOT_TOKEN: Slack 通知を使う場合
     - SLACK_CHANNEL_ID: Slack チャンネル ID（通知を使う場合）
   - 任意:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...

5. DuckDB スキーマを初期化
   - 例（Python REPL / スクリプト）:
     - from kabusys.config import settings
       from kabusys.data.schema import init_schema
       conn = init_schema(settings.duckdb_path)
   - :memory: を渡せばインメモリ DB での利用も可能。

---

## 使い方（代表的なワークフロー例）

以下は Python スクリプトや REPL から実行する最小例です。

1. DB 初期化（1度だけ）
   - from kabusys.config import settings
     from kabusys.data.schema import init_schema
     conn = init_schema(settings.duckdb_path)

2. 日次 ETL を実行（J-Quants から差分取得して保存）
   - from kabusys.data.pipeline import run_daily_etl
     res = run_daily_etl(conn)  # 戻り値は ETLResult オブジェクト
     print(res.to_dict())

3. ファーチャー作成（戦略層: features テーブルへ書き込み）
   - from datetime import date
     from kabusys.strategy import build_features
     cnt = build_features(conn, date(2024, 1, 1))
     print(f"upserted features: {cnt}")

4. シグナル生成（features / ai_scores / positions を参照して signals を作成）
   - from kabusys.strategy import generate_signals
     total_signals = generate_signals(conn, date(2024, 1, 1))
     print(f"signals generated: {total_signals}")

   - 生成時に重みや閾値をカスタム指定可能:
     - generate_signals(conn, date(...), threshold=0.65, weights={"momentum":0.5, "value":0.2, ...})

5. ニュース収集（RSS）
   - from kabusys.data.news_collector import run_news_collection
     from kabusys.research.factor_research import calc_momentum  # で known_codes を生成するなど
     known_codes = {"7203", "6758", ...}  # 有効銘柄コードの集合
     result = run_news_collection(conn, known_codes=known_codes)
     print(result)  # ソースごとの新規保存数を返す

6. マーケットカレンダーの更新ジョブ
   - from kabusys.data.calendar_management import calendar_update_job
     saved = calendar_update_job(conn)
     print(f"calendar saved: {saved}")

ログレベルや挙動は環境変数（KABUSYS_ENV, LOG_LEVEL）で制御できます。KABUSYS_ENV は development / paper_trading / live のいずれかを設定してください。

---

## 主要モジュール・関数の要点

- kabusys.config
  - settings: 必須設定のアクセスラッパ（settings.jquants_refresh_token 等）
  - .env 自動読み込み（プロジェクトルート基準）。無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token: リフレッシュトークン → ID トークン（自動リフレッシュと 401 ハンドリング）
  - レート制御（120 req/min）、リトライ（指数バックオフ）を組み込み

- kabusys.data.schema
  - init_schema(db_path): DuckDB に全テーブルを作成して接続を返す
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...): 日次 ETL（カレンダー、価格、財務、品質チェック）
  - get_last_price_date 等の差分更新ユーティリティ

- kabusys.research.factor_research
  - calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials を用いたファクター計算

- kabusys.strategy.feature_engineering
  - build_features(conn, target_date): ファクター合成・正規化・features テーブルへ UPSERT

- kabusys.strategy.signal_generator
  - generate_signals(conn, target_date, threshold, weights): final_score を計算して BUY/SELL を signals テーブルへ保存

- kabusys.data.news_collector
  - fetch_rss / save_raw_news / run_news_collection
  - RSS の安全な取得（SSRF 対策、gzip 上限、defusedxml）と銘柄抽出ロジック

---

## ディレクトリ構成（概要）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - schema.py
    - stats.py
    - news_collector.py
    - calendar_management.py
    - features.py
    - audit.py
    - calendar_management.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/ (存在宣言のみ: 実装を想定)

各ファイルはモジュールドキュメント文字列（docstring）で目的・設計・処理フローを詳述しています。実装関数の docstring を参照してください。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須 if using kabu 発注)
- KABU_API_BASE_URL (任意): kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須 if using Slack)
- SLACK_CHANNEL_ID (必須 if using Slack)
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意): 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV (任意): development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意): DEBUG/INFO/...

---

## 運用上の注意

- J-Quants の API レート制限（120 req/min）を尊重してください。jquants_client は固定間隔のレートリミッタを実装していますが、短時間に大量リクエストを投げる設計は避けてください。
- DuckDB の ON CONFLICT/RETURNING に依存している箇所があります。DuckDB のバージョン互換性に注意してください。
- ニュース収集は外部 URL を取得するため SSRF や大容量レスポンス等の安全対策（実装済み）に依存しますが、社内ネットワークポリシー等に従って下さい。
- 本リポジトリは研究・自動化用のフレームワーク基盤を提供します。実運用（特に live）では追加のリスク管理（注文量制限、発注監査、フェイルセーフ等）を必ず実装してください。

---

## 貢献・拡張ポイント

- execution 層のブローカー固有アダプタ実装（kabuステーション連携ラッパ）
- モニタリング / アラート（Slack 通知ラッパの追加）
- AI スコア生成パイプライン（ai_scores テーブルへの導入）
- テストカバレッジと CI（J-Quants のモックを組み込んだ単体テスト）

---

README に含める他の具体的な例や、CI 設定・Docker 化・運用プレイブック等が必要であれば教えてください。必要に応じて .env.example のテンプレートも作成します。