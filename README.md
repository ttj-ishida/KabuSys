# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP、ファクター・リサーチ、監査ログ等を含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構築するための基盤ライブラリです。主な目的は次のとおりです。

- J-Quants API からのデータ取得（株価日足、財務、マーケットカレンダー）
- DuckDB を用いたデータ保存・ETL パイプライン
- RSS からのニュース収集と LLM を用いたニュースセンチメント解析
- 市場レジーム判定（MA200 と マクロニュースの合成）
- 研究（ファクター計算・将来リターン・IC 計算）用ユーティリティ
- 監査ログ（signal → order_request → execution）のためのスキーマ初期化
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上、バックテストでの「ルックアヘッドバイアス」を避ける工夫（API 呼び出し・現在日参照の厳格制御）が施されています。

---

## 機能一覧（主な公開 API / モジュール）

- kabusys.config
  - 環境変数の自動読み込み（.env / .env.local）と settings オブジェクト
- kabusys.data.jquants_client
  - J-Quants API からのデータ取得・保存（fetch_* / save_*）
  - 認証トークン取得（get_id_token）
- kabusys.data.pipeline
  - 日次 ETL 実行（run_daily_etl）、個別 ETL（run_prices_etl 等）
  - ETLResult データクラス
- kabusys.data.news_collector
  - RSS フィード収集・前処理・raw_news への格納ロジック
- kabusys.ai.news_nlp
  - ニュース記事を銘柄ごとに LLM でスコアリング（score_news）
- kabusys.ai.regime_detector
  - MA200 と マクロニュース LLM を合成した市場レジーム判定（score_regime）
- kabusys.research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - フィーチャー探索（calc_forward_returns / calc_ic / factor_summary / rank）
- kabusys.data.quality
  - データ品質チェック群（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
- kabusys.data.audit
  - 監査ログ用スキーマの初期化（init_audit_schema, init_audit_db）
- 共通ユーティリティ
  - kabusys.data.stats.zscore_normalize

---

## セットアップ手順

前提
- Python 3.10 以降（型注釈に `X | None` を使用）
- DuckDB, OpenAI SDK, defusedxml などが必要

推奨手順（UNIX 系）:

1. リポジトリをクローン／配置
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate
3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （ローカル開発時は editable install）
     - pip install -e .

   ※ 実際の requirements.txt / pyproject.toml がある場合はそれに従ってください。

4. 環境変数を用意する
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと、自動で読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（主要なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - SLACK_BOT_TOKEN — Slack 通知用（必要に応じて）
     - SLACK_CHANNEL_ID
     - KABU_API_PASSWORD — kabu API のパスワード
     - OPENAI_API_KEY — OpenAI を利用する場合（score_news / score_regime）
   - オプション:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV（development / paper_trading / live）
     - LOG_LEVEL（DEBUG / INFO / ...）

5. DuckDB 用の初期スキーマ（監査ログなど）を作成する場合:
   - Python から init_audit_db を呼ぶ（下記 使い方 参照）

---

## 使い方（簡単なコード例）

以下は代表的な使い方例です。実行前に .env（または環境変数）で必要なキーを設定しておいてください。

- ETL（日次 ETL を実行）
  - 例:
    - from datetime import date
      import duckdb
      from kabusys.data.pipeline import run_daily_etl
      from kabusys.config import settings

      conn = duckdb.connect(str(settings.duckdb_path))
      result = run_daily_etl(conn, target_date=date(2026, 3, 20))
      print(result.to_dict())

- ニューススコアリング（OpenAI を用いる）
  - 例:
    - from datetime import date
      import duckdb
      from kabusys.ai.news_nlp import score_news
      from kabusys.config import settings

      conn = duckdb.connect(str(settings.duckdb_path))
      # OPENAI_API_KEY を環境変数に設定するか、api_key 引数で指定
      n_written = score_news(conn, target_date=date(2026, 3, 20))
      print("scored:", n_written)

- 市場レジーム判定
  - 例:
    - from datetime import date
      import duckdb
      from kabusys.ai.regime_detector import score_regime
      from kabusys.config import settings

      conn = duckdb.connect(str(settings.duckdb_path))
      score_regime(conn, target_date=date(2026, 3, 20))

- 監査 DB 初期化（監査ログ専用 DB を作る）
  - 例:
    - from kabusys.data.audit import init_audit_db
      conn = init_audit_db("data/audit.duckdb")
      # これで監査テーブルが作成されます

- J-Quants の id_token を取得
  - 例:
    - from kabusys.data.jquants_client import get_id_token
      token = get_id_token()  # JQUANTS_REFRESH_TOKEN が環境変数にある前提

注意点:
- score_news / score_regime などの関数は OpenAI API キーを必要とします（api_key 引数で上書き可能）。
- run_daily_etl は ETL の各ステップで失敗を吸収しつつ処理を継続し、ETLResult に結果と品質チェック結果を返します。

---

## 環境変数（主要一覧）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知設定
- DUCKDB_PATH — DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB パス（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視設定
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化

.env の自動読み込みは、プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に行われます。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ公開
- config.py — 環境変数管理 / Settings
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）および ETLResult
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 収集・前処理
  - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
  - quality.py — データ品質チェック
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン、IC、統計サマリーなど

各モジュールはドキュメント文字列と注釈が豊富で、単体で読むことで利用方法が分かるように設計されています。

---

## 運用上の注意・補足

- セキュリティ
  - news_collector は SSRF 対策、受信サイズ制限、XML パーサの安全実装（defusedxml）を備えています。
  - J-Quants クライアントはレート制御とトークン自動リフレッシュ、リトライを実装しています。
- フェイルセーフ設計
  - LLM 呼び出し失敗時はスコアを 0 にフォールバックする等、致命的な例外により全処理が止まらない方針を採っています。
- バックテストに使う際
  - Look-ahead バイアス防止のため、関数は内部で現在日時を参照しないよう設計されていますが、バックテスト用にはデータ取得タイミングと DB 内容に注意してください。
- Python バージョン
  - ソースは Python 3.10+ の構文（| 型など）を使用しています。

---

## サポート / 開発

- 新しい機能追加やバグ修正を行う場合は、関連モジュール（ETL / news_nlp / jquants_client / audit）に対してユニットテストを追加してください。
- 環境変数の設定ミスで起きるエラーは config.Settings により早期に検出されます。実運用前に .env を整備してください。

---

上記で README の基本的な情報は網羅しています。必要であれば、セットアップ向けの具体的な requirements.txt、起動スクリプト例、あるいは CI / デプロイ手順（systemd サービス定義や Cron/スケジューラ設定例）を追加します。どの情報を追加しますか？