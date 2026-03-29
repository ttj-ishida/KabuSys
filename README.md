# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得・保存）、ニュース収集・NLP スコアリング（OpenAI 使用）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的を想定した内部向けライブラリです。

- J-Quants API から株価・財務・カレンダーを差分で取得して DuckDB に保存する ETL。
- RSS からニュースを収集し raw_news を生成。銘柄紐付けと前処理を行う。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別）とマクロセンチメント（市場レジーム判定）。
- 監査ログ（signal → order_request → execution）を DuckDB に冪等的に初期化・保存するユーティリティ。
- 研究用のファクター計算（モメンタム／ボラティリティ／バリュー等）と統計ユーティリティ。
- データ品質チェック（欠損、重複、スパイク、日付不整合）機能。

設計上の特徴:
- ルックアヘッドバイアスを避ける実装（内部で datetime.today() を不用意に参照しない等）。
- API 呼び出しに対するリトライ、レート制御、フェイルセーフ（失敗時は安全に継続）を重視。
- DuckDB を中心に SQL + Python で効率的に処理。

---

## 機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（token 取得、daily_quotes / financials / calendar の fetch/save）
  - カレンダー管理（営業日判定、next/prev trading day、calendar update job）
  - ニュース収集（RSS 取得、前処理、SSRF 対策）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマ初期化 / DB 作成（init_audit_schema, init_audit_db）
  - 汎用統計（zscore 正規化）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを取得して ai_scores に書き込む
  - regime_detector.score_regime: ETF とマクロニュースを合成して market_regime に書き込む
- research/
  - factor 計算: calc_momentum, calc_value, calc_volatility
  - feature exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config
  - 環境変数・設定管理（.env 自動読み込み機能、必須キー取得 helper）

---

## セットアップ手順

前提
- Python 3.10+（typing の union 表記や型ヒントを使用）
- DuckDB を利用（ローカルファイルや :memory:）

推奨インストール（例）
1. 仮想環境を作成・有効化
   - python -m venv .venv && source .venv/bin/activate

2. 必要パッケージをインストール（最低限）
   - pip install duckdb openai defusedxml

   ※プロジェクト固有の依存リストがある場合は requirements.txt / poetry を使用してください。

3. 環境変数を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと config モジュールが自動で読み込みます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
- OPENAI_API_KEY: OpenAI 呼び出し用 API キー（news_nlp, regime_detector）
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注モジュールを使う場合）
- SLACK_BOT_TOKEN: Slack 通知に使用する場合
- SLACK_CHANNEL_ID: Slack 通知チャンネル

任意環境変数（デフォルト値あり）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）

注意: .env の書式は POSIX ライクな KEY=VALUE、引用符・エスケープ等に対応。`.env.example` を参考に作成してください（プロジェクトに含めることを推奨）。

---

## 使い方（主要例）

以下は Python REPL またはスクリプトでの利用例です。

- DuckDB 接続を作る（ファイル DB）
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))  # settings は kabusys.config.settings

- 日次 ETL を実行する
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースセンチメントを取得して書き込む（OpenAI API Key 必須）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")  # api_key 引数は省略可能（環境変数を使用）

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 研究用ファクター計算
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - mom = calc_momentum(conn, date(2026,3,20))
  - val = calc_value(conn, date(2026,3,20))

- 監査ログ DB 初期化
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")

- データ品質チェックを実行
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=date(2026,3,20))
  - for i in issues: print(i)

Tips
- OpenAI 呼び出しは API レート・費用がかかるため、テスト時は api_key をモックするか少量のデータで試してください。
- ETL 実行前に market_calendar 等のスキーマが必要です。ETL は通常既存スキーマを前提に動きます（スキーマ初期化ロジックを別途用意している可能性があります）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                 -- 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py             -- ニュースセンチメント（OpenAI）
    - regime_detector.py      -- 市場レジーム判定（ETF MA + マクロ LLN）
  - data/
    - __init__.py
    - jquants_client.py       -- J-Quants API クライアント + DuckDB 保存
    - pipeline.py             -- ETL パイプライン（run_daily_etl 等）
    - etl.py                  -- ETL 結果の公開（ETLResult）
    - news_collector.py       -- RSS 取得 / 前処理 / raw_news 保存
    - calendar_management.py  -- 市場カレンダー管理（is_trading_day 等）
    - stats.py                -- 統計ユーティリティ（zscore_normalize）
    - quality.py              -- データ品質チェック
    - audit.py                -- 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py      -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py  -- forward returns / IC / summary / rank

（上記は主要モジュールのみを抜粋しています。詳細はソースを参照してください）

---

## 実運用上の注意点

- 秘密情報（API キー等）は .env/.env.local で管理し、リポジトリにコミットしないでください。
- OpenAI と J-Quants の API 呼び出しは課金やレート制限に注意してください。
- 本ライブラリはバックテスト用途の補助とデータ基盤整備を意図しており、実際の発注・運用時は十分なリスク管理と検証が必要です。
- DuckDB のバージョン差異による挙動（executemany の空リスト制約など）に注意してください（実装内で対応済みの箇所あり）。

---

もし README に加えたい実例（.env.example のテンプレート、set-up script、CI 実行方法やサンプルデータの作り方等）があれば教えてください。それに合わせて追記します。