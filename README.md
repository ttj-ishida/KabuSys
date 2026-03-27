# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースセンチメント（LLM）、市場レジーム判定、研究用ファクター計算、監査ログなどを含むモジュール群を提供します。

主な設計方針は「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（API失敗時の継続）」「DuckDBベースの高速分析」です。

---

## 機能一覧

- 環境設定管理
  - .env 自動ロード（プロジェクトルートを探索、`.env` / `.env.local` を読み込み）
  - 必須環境変数の取得とバリデーション

- データ取得・ETL（J-Quants API）
  - 株価日足（OHLCV）取得・保存（ページネーション対応、レート制御、リトライ）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - 差分更新ロジック・バックフィル・ETL パイプライン（run_daily_etl）

- データ品質チェック
  - 欠損（OHLC）検出、スパイク（急騰・急落）検出、重複チェック、日付整合性チェック
  - QualityIssue オブジェクトで問題を集約

- ニュース収集
  - RSS フィード取得（SSRF対策、gzip対応、トラッキングパラメータ除去）
  - テキスト前処理、raw_news / news_symbols への冪等保存設計

- AI（OpenAI）連携
  - ニュースごとの銘柄センチメント集計（news_nlp.score_news）
  - マクロ × ETF MA に基づく市場レジーム判定（regime_detector.score_regime）
  - OpenAI 呼出しはリトライやフォールバック実装済み（失敗時は中立値で継続）

- 研究ユーティリティ
  - モメンタム / ボラティリティ / バリュー系ファクター計算
  - 将来リターン計算、IC（Spearman）計算、Zスコア正規化、統計サマリー

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブル定義と初期化（init_audit_schema / init_audit_db）
  - 発注フローのUUID連鎖によるトレーサビリティ保証

---

## 必要条件（推奨）

- Python 3.10 以上（タイプヒントに `|` 演算子等を使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

実際のプロジェクトでは pyproject.toml / requirements.txt に依存関係を明記してください。

---

## セットアップ手順

1. リポジトリをチェックアウト／クローン

2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （パッケージ群はプロジェクトに応じて追加してください）

4. パッケージをインストール（編集可能モード）
   - pip install -e .

5. 環境変数を設定
   - ルート（.git または pyproject.toml があるディレクトリ）に `.env`（および任意で `.env.local`）を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数（コード内 Settings より）:
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN       : Slack Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
- OPENAI_API_KEY        : OpenAI API キー（AI 機能を使う場合）
- 省略時のデフォルト:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト "development"
  - LOG_LEVEL (DEBUG|INFO|...) — デフォルト "INFO"
  - DUCKDB_PATH — デフォルト "data/kabusys.duckdb"
  - SQLITE_PATH — デフォルト "data/monitoring.db"
  - KABU_API_BASE_URL — デフォルト "http://localhost:18080/kabusapi"

例（.env）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABU_API_PASSWORD=your_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（基本例）

以下はライブラリ API を直接呼ぶ簡単な例です。実運用ではログ設定やエラーハンドリングを適切に行ってください。

- DuckDB 接続の作成例
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（run_daily_etl）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=None)  # target_date を与えることも可
  - print(result.to_dict())

- ニュースセンチメントスコアの算出（AI）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n_written = score_news(conn, target_date=date(2026,3,20))
  - print(f"written scores: {n_written}")

  - score_news は OPENAI_API_KEY 環境変数を参照します。api_key 引数で上書き可能。

- 市場レジーム判定（ETF + マクロ）
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026,3,20))

- 監査ログ DB 初期化（監査専用 DB を作る）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可

- ETL の個別ジョブ（例: 株価 ETL）
  - from kabusys.data.pipeline import run_prices_etl
  - run_prices_etl(conn, target_date=date(2026,3,20), id_token=None)

- ニュース RSS 収集（低レベルユーティリティ）
  - from kabusys.data.news_collector import fetch_rss
  - articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")

---

## 注意点 / 実装上のポイント

- ルックアヘッドバイアス防止:
  - 多くの関数は内部で datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る設計です。バッチ・バックテストでの使用を想定した実装です。

- 冪等性:
  - J-Quants からの保存は ON CONFLICT DO UPDATE を用いた冪等保存を行います。
  - ニュース収集は URL 正規化 → SHA-256 による記事IDで冪等性を担保します。

- フェイルセーフ:
  - OpenAI 等の外部 API 呼び出しが失敗した場合、致命的に停止させず中立値（0.0）で処理を継続するケースが多くあります（ログは出力されます）。

- 環境変数自動ロード:
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動読み込みします。テストで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py (パッケージ定義, __version__)
  - config.py (環境変数・設定管理)
  - ai/
    - __init__.py (score_news を公開)
    - news_nlp.py (ニュースセンチメント集計, score_news)
    - regime_detector.py (市場レジーム判定, score_regime)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント: fetch_*/save_* 実装)
    - pipeline.py (ETLパイプライン run_daily_etl, run_*_etl)
    - etl.py (ETLResult 再エクスポート)
    - news_collector.py (RSS 収集・前処理)
    - calendar_management.py (マーケットカレンダー管理、営業日判定)
    - quality.py (データ品質チェック)
    - stats.py (zscore_normalize 等)
    - audit.py (監査ログスキーマ初期化、init_audit_db)
  - research/
    - __init__.py
    - factor_research.py (calc_momentum, calc_value, calc_volatility)
    - feature_exploration.py (calc_forward_returns, calc_ic, factor_summary, rank)

---

## よくある使い方 / Tips

- OpenAI API を多用する処理（news_nlp, regime_detector）は API への連続呼び出しを行います。利用量に注意してください。
- J-Quants の API レート制御は内部で行われていますが、大量のページネーション呼び出しを行う際は `id_token` のキャッシュや backfill 設定に注意してください。
- DuckDB をファイルで永続化する際はパスの親ディレクトリを事前に作成するか、init_audit_db が自動作成するのを利用してください。
- テスト時は各種外部呼び出し（OpenAI, HTTP, jquants）をモックすると良いです。モジュール内で `_call_openai_api` 等を差し替えやすく設計されています。

---

この README はコードベースの主要な使い方と設計意図を凝縮したものです。より詳細な使い方・設定や運用ルールはプロジェクトのドキュメント（Design/Platform.md や StrategyModel.md 等）を参照してください。必要であればサンプルスクリプトや運用手順（cron / CI ワークフロー例）も作成します。