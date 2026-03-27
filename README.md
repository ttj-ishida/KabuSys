# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL・データ品質チェック・ニュース収集・AIによるニュースセンチメント評価・市場レジーム判定・リサーチ用ファクター計算・監査ログ構築などを含むモジュール群を提供します。

## 主な特徴
- J-Quants API からの差分ETL（株価・財務・上場銘柄・市場カレンダー）
- DuckDB を用いたローカルデータストアへの冪等保存（ON CONFLICT DO UPDATE）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- RSSベースのニュース収集と銘柄紐付け（SSRF対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄単位・マクロ）
- ETF（1321）200日移動平均とマクロセンチメントの合成による市場レジーム判定
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）と統計ユーティリティ
- 監査ログ（signal → order_request → executions）のスキーマ初期化ユーティリティ
- 環境変数／.env による設定管理（プロジェクトルート自動検出）

---

## 機能一覧（モジュールハイライト）
- kabusys.config
  - .env 自動読み込み（.env, .env.local）、必須環境変数取得ユーティリティ
- kabusys.data
  - jquants_client: J-Quants API ラッパー（レートリミット・リトライ・トークン自動更新）
  - pipeline: 日次 ETL（run_daily_etl）と個別 ETL ジョブ（prices/financials/calendar）
  - quality: データ品質チェック群（run_all_checks）
  - news_collector: RSS 取得・テキスト前処理・raw_news 保存
  - calendar_management: 営業日判定やカレンダー更新ジョブ
  - audit: 監査ログテーブルの初期化（init_audit_db / init_audit_schema）
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: ma200 とマクロセンチメントを合成して market_regime に書き込む
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを展開
2. Python 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール  
   （実プロジェクトでは requirements.txt / pyproject.toml を参照してください。ここは代表的依存の例です）
   ```bash
   pip install duckdb openai defusedxml
   ```
4. 環境変数（または .env）を用意  
   プロジェクトルート（.git または pyproject.toml を基準）に `.env` または `.env.local` を置くと自動で読み込まれます（自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   代表的な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネルID（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   - DUCKDB_PATH: デフォルト data/kabusys.duckdb（任意）
   - SQLITE_PATH: デフォルト data/monitoring.db（任意）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB 用ディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要なユースケース例）

以下は Python REPL / スクリプトから呼び出す使い方例です。いずれも duckdb.connect で接続オブジェクトを渡します。

- ETL（日次パイプライン）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄単位）を評価して ai_scores に書き込む
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote {written} scores")
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメント合成）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査DB初期化（監査専用 DB を作る場合）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用：ファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(records[:5])
  ```

注意:
- AI 機能（score_news / score_regime）は OPENAI_API_KEY（引数でも可）が必要です。
- run_daily_etl はデフォルトで品質チェックを行います（run_quality_checks 引数で制御）。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数/.env 管理
  - ai/
    - __init__.py
    - news_nlp.py                   -- 銘柄別ニュースセンチメント（score_news）
    - regime_detector.py            -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント & 保存関数
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - etl.py                        -- ETLResult の再エクスポート
    - news_collector.py             -- RSS 取得・前処理
    - calendar_management.py        -- 市場カレンダー管理（is_trading_day など）
    - quality.py                    -- データ品質チェック
    - stats.py                      -- zscore_normalize 等
    - audit.py                      -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            -- calc_momentum / calc_value / calc_volatility
    - feature_exploration.py        -- calc_forward_returns / calc_ic / factor_summary / rank
  - ai、research、data のその他モジュール（詳細はソース参照）

---

## 実運用上の注意点
- 環境（KABUSYS_ENV）には "development" / "paper_trading" / "live" のいずれかを設定してください。live 環境では実際の発注等のガードを厳格に行う運用が必要です。
- J-Quants API にはレート制限があるため jquants_client は内部でスロットリング・リトライを行います。大量並列でのリクエストは避けてください。
- OpenAI API 呼び出しはコストとレイテンシに注意し、バッチ化（news_nlp の BATCH_SIZE など）を活用してください。
- DuckDB に書き込む際は ON CONFLICT 等で冪等性を保つ設計になっていますが、運用時はバックアップ方針を検討してください。
- .env 自動ロードはプロジェクトルート（.git 或いは pyproject.toml）を基準に行われます。テスト等で自動ロードを抑制する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 貢献・拡張
- 新しいニュースソースの追加は data/news_collector.py の DEFAULT_RSS_SOURCES を拡張してください。
- 新しい品質チェックは data/quality.py に追加し run_all_checks に組み込むことで ETL フローに組み込めます。
- OpenAI モデルやプロンプトの調整は ai/news_nlp.py / ai/regime_detector.py の _SYSTEM_PROMPT / モデル定数を編集してください。
- DuckDB スキーマを変更する場合は data.audit や ETL の保存関数側も併せて更新してください。

---

この README はソースコードの主要機能と使い方を簡潔にまとめたものです。詳細な挙動や追加設定は各モジュール（src/kabusys/**）の docstring を参照してください。必要があれば README のサンプルコマンドや .env.example を追加で作成します。どの情報を優先して追記したいか教えてください。