# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP、研究用ファクター計算、監査ログ（発注トレーサビリティ）などの機能を提供します。

主な対象:
- 日次 ETL による株価・財務・市場カレンダーの取得・保存（DuckDB）
- RSS ベースのニュース収集と LLM を使った記事・マクロ判定（OpenAI）
- ファクター計算 / 特徴量探索（研究用途）
- 監査ログテーブル（発注 → 約定のトレーサビリティ）
- データ品質チェック

注意: 本リポジトリはライブラリ群を提供します。実際の発注（ブローカー接続）や本番運用は利用者の責任で行ってください。

## 機能一覧
- 環境設定管理（.env 自動読み込み、必須項目の検証）
- J-Quants API クライアント（差分取得、レート制御、リトライ、トークンリフレッシュ）
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- 市場カレンダー管理（営業日判定 / next/prev_trading_day / calendar_update_job）
- ニュース収集（RSS → raw_news、SSRF 対策、トラッキング除去、記事ID正規化）
- ニュース NLP（gpt-4o-mini を用いた銘柄別センチメント score_news）
- 市場レジーム判定（ETF 1321 の MA とマクロセンチメントを合成して score_regime）
- 研究用ファクター計算（momentum / value / volatility 等）
- 統計ユーティリティ（zscore_normalize 等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ初期化と DB ヘルパー（init_audit_db / init_audit_schema）

## セットアップ手順（開発環境）
前提:
- Python 3.10 以上（型注釈に新しい union 表記を使用）
- DuckDB, OpenAI SDK 等の依存パッケージ

1. リポジトリをクローン／配置
   - 任意の場所に配置してください。

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - macOS / Linux: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   （プロジェクトで requirements.txt を用意している場合はそれを使用してください）

4. 環境変数を設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 最低限設定が必要な環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - OPENAI_API_KEY : OpenAI API キー（score_news / score_regime で使用）
     - KABU_API_PASSWORD : kabuステーション API パスワード（使用する場合）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID : Slack 通知を使う場合
   - 追加設定（デフォルト値あり）:
     - KABUSYS_ENV = development | paper_trading | live  (default: development)
     - LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL (default: INFO)
     - KABUSYS_DISABLE_AUTO_ENV_LOAD = 1 （自動 .env 読み込みを無効化）
     - DUCKDB_PATH（default: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 default: data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB データベース初期化（監査ログ用）
   - Python REPL またはスクリプトから:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

## 使い方（代表的な API）
以下はライブラリの代表的な呼び出し例です。必要に応じてログ設定やエラーハンドリングを追加してください。

- DuckDB 接続の作成
  from datetime import date
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行（J-Quants からデータ取得）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニュース NLP（銘柄別センチメント）を実行
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026,3,20))
  print("scored:", n_written)

- 市場レジーム判定を実行
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20))

- 監査ログテーブルを初期化（既存 DB に追加）
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

- データ品質チェックを実行
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)

注意点:
- score_news / score_regime は OpenAI API キー（OPENAI_API_KEY）を必要とします。api_key 引数を直接渡すことも可能です。
- ETL は J-Quants の API レート制限・認証を考慮した実装になっていますが、実行前に J-Quants の利用規約とレート制限をご確認ください。
- DuckDB のテーブルスキーマ（raw_prices, raw_financials, market_calendar, raw_news, ai_scores, news_symbols, ai_scores など）は想定されています。ETL を実行する前にスキーマが作成されているか確認してください（別モジュールで schema 初期化を提供することを想定）。

## ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定管理（.env 自動ロード含む）
- ai/
  - __init__.py
  - news_nlp.py            — ニュースセンチメント（score_news）
  - regime_detector.py     — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（fetch / save 関数）
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - etl.py                 — ETLResult の再エクスポート
  - calendar_management.py — 市場カレンダー管理 / calendar_update_job
  - stats.py               — 統計ユーティリティ（zscore_normalize）
  - quality.py             — データ品質チェック
  - audit.py               — 監査ログ（テーブル定義・初期化）
  - news_collector.py      — RSS ニュース取得・前処理（SSRF 対策など）
- research/
  - __init__.py
  - factor_research.py     — Momentum/Value/Volatility 等の計算
  - feature_exploration.py — forward returns / IC / factor summary / rank

（開発中のファイル群や補助モジュールが含まれます）

## 備考 / 運用上の注意
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を起点）を検出して .env/.env.local を読み込みます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効にできます。
- OpenAI 呼び出しはリトライやフェイルセーフを備えていますが、API 使用料が発生します。テスト時は該当関数をモックすることを推奨します（module 内の _call_openai_api をパッチする等）。
- ETL や API 呼び出しはネットワーク・外部サービス依存のため、エラー発生時のログとリトライ挙動を確認してください。
- 本プロジェクトはデータの「取得・分析」レイヤーを提供するものであり、実際の発注ロジック（ブローカ接続、リスク管理、ポジション管理）を組み合わせる必要があります。発注処理は十分なテストを行ってください。

---

この README はコードベースを元に作成しています。追加の使い方やスクリプト（CLI / サービス起動スクリプト）、テーブルスキーマ定義ファイルなどがあれば README を拡張してください。質問があれば使い方や具体的な例（ETL の初回実行手順、DB スキーマ初期化スクリプトなど）を追記します。