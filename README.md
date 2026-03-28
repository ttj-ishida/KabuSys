# KabuSys

日本株の自動売買・データ基盤ライブラリ（軽量プロトタイプ）

KabuSys は日本株向けのデータプラットフォーム、リサーチ、AI 支援（ニュース NLP / 市場レジーム判定）、および監査ログ／ETL ユーティリティ群を提供する Python パッケージです。J-Quants API と連携した日次 ETL、RSS ベースのニュース収集、OpenAI を使ったニュースセンチメント解析など、自動売買システム構築に必要な基盤機能を含みます。

主な設計方針:
- ルックアヘッドバイアスを避ける（date.today()/datetime.today() を直接参照しない設計）
- DuckDB をデータ層に利用（オンディスク / in-memory）
- 冪等性を重視した ETL / DB 書き込み
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフ実装
- セキュリティ考慮（RSS の SSRF 対策、defusedxml など）

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（株価日足、財務データ、JPX カレンダー、上場銘柄一覧）
  - 差分更新・バックフィル付きの日次 ETL（run_daily_etl）
  - market_calendar の夜間更新ジョブ
  - DuckDB への冪等保存関数（raw_prices, raw_financials, market_calendar 等）

- データ品質チェック
  - 欠損検出、スパイク検出（前日比閾値）、重複チェック、日付整合性チェック
  - QualityIssue による問題の集約（run_all_checks）

- ニュース収集 / 前処理
  - RSS フィード取得（トラッキングパラメータ除去、URL 正規化）
  - SSRF 対策、受信サイズ制限（Gzip 対応）
  - raw_news / news_symbols への冪等保存設計（記事 ID は URL 正規化後ハッシュ）

- AI（OpenAI）
  - ニュース NLP スコアリング（銘柄ごとの sentiment → ai_scores へ書込）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）
  - OpenAI 呼び出しは JSON mode を利用し、リトライ・エラーハンドリング済み

- リサーチ / ファクター計算
  - Momentum（1M/3M/6M、MA200乖離）
  - Volatility（ATR20、相対ATR、出来高系）
  - Value（PER, ROE）
  - 将来リターン計算、IC（Spearman ランク相関）、ファクター統計サマリー
  - Zスコア正規化ユーティリティ

- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - 発注のトレーサビリティ（UUID ベースの階層化）

- 設定管理
  - .env と環境変数の自動読み込み（パッケージルートを基準）
  - 必須環境変数のラッパー（settings オブジェクト）

---

## 必要条件

- Python 3.10 以上（型ヒントで | を使用）
- 主要依存（例）
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ（urllib, datetime, logging 等）

実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <this-repo>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （開発中は pip install -e . で編集可能インストール）

4. 環境変数 / .env を準備
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に .env を置くと自動読み込みされます。
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

   必須（例）:
   - JQUANTS_REFRESH_TOKEN=（J-Quants リフレッシュトークン）
   - KABU_API_PASSWORD=（kabu API パスワード）
   - SLACK_BOT_TOKEN=（Slack bot token）
   - SLACK_CHANNEL_ID=（通知先 Slack チャンネル ID）
   - OPENAI_API_KEY=（OpenAI API キー） — AI 機能を使う場合

   任意 / デフォルト:
   - KABUSYS_ENV=development|paper_trading|live  (デフォルト development)
   - LOG_LEVEL=INFO (デフォルト)
   - KABU_API_BASE_URL (デフォルト http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト data/monitoring.db)

   .env の書式は Bash 形式（export を含めた行やコメントを扱える）です。

---

## 使い方（コード例）

以下は基本的な利用例です。実行前に必要な環境変数を設定してください。

- 設定・パス取得
  - from kabusys.config import settings
  - settings.duckdb_path などでパスを取得できます。

- DuckDB 接続を開く
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- ETL を日次実行（市場カレンダー / 株価 / 財務 / 品質チェックを含む）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # 戻り値は ETLResult（詳細は pipeline.ETLResult）

- ニュースのセンチメントスコア（OpenAI 必須）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026,3,20))  # 書込み銘柄数を返す

- 市場レジーム判定（OpenAI 必須）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026,3,20))

- ファクター計算（Research）
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - mom = calc_momentum(conn, target_date=date(2026,3,20))

- 将来リターン / IC / 統計
  - from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
  - fwd = calc_forward_returns(conn, target_date=date(2026,3,20))
  - ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
  - summary = factor_summary(mom, ["mom_1m", "ma200_dev"])

- 監査ログ DB 初期化
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db(settings.duckdb_path)  # transactional=True を指定することも可能

- RSS フィード取得（ニュース収集）
  - from kabusys.data.news_collector import fetch_rss
  - articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")

Notes:
- OpenAI 呼び出しを行う関数は api_key 引数で明示的にキーを渡すことができます（テストや複数キー運用向け）。
- ETL / API 呼び出しは外部ネットワークに依存するため、例外処理や retry を適切に行ってください。

---

## 簡単なワークフロー例

1. 初期化
   - DuckDB を用意し（settings.duckdb_path）、監査スキーマを作成。
2. 夜間バッチ
   - run_daily_etl を cron / Airflow 等でスケジューリング。
   - calendar_update_job や run_calendar_etl は ETL 内で実行されます。
3. ニュース解析 & レジーム判定
   - score_news → ai_scores を更新
   - score_regime → market_regime を更新
4. リサーチ
   - calc_* 系関数でファクターを計算し、戦略作成に利用
5. 発注監査
   - 発注は order_requests テーブルに書き込み、約定は executions テーブルで追跡

---

## 主要ファイル / ディレクトリ構成

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数/.env 読込 & settings
  - ai/
    - __init__.py
    - news_nlp.py          — ニュース NLP（銘柄ごとのスコア算出）
    - regime_detector.py   — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - etl.py               — ETLResult の再エクスポート
    - calendar_management.py — 市場カレンダー判定 / 更新ジョブ
    - news_collector.py    — RSS ニュース収集（SSRF 対策・前処理）
    - quality.py           — データ品質チェック（missing/spike/duplicates/etc）
    - stats.py             — zscore_normalize 等の統計ユーティリティ
    - audit.py             — 監査ログスキーマ初期化（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py   — Momentum / Volatility / Value 計算
    - feature_exploration.py — forward returns, IC, rank, factor_summary
  - ai/、research/、data/ 以下は相互依存を最小化するよう設計されています。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD — kabu API パスワード（発注系で使用）
- SLACK_BOT_TOKEN — Slack 通知に使用
- SLACK_CHANNEL_ID — Slack 通知先チャンネル
- OPENAI_API_KEY — OpenAI API キー（AI 関連機能を使用する場合）

任意:
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

---

## テスト / 開発のヒント

- OpenAI 呼び出しやネットワーク依存部分はモック化可能（各モジュール内に _call_openai_api のラッパーがありテスト用に patch しやすい設計）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml がある階層）から行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使うと環境切替が容易です。
- DuckDB はインメモリ接続（":memory:"）でも初期化できます（audit.init_audit_db(":memory:")）。

---

## 貢献 / ライセンス

この README はコードベースから自動生成した要点をまとめたものです。実運用や公開配布の前にセキュリティ・法務・取引アルゴリズムの確認を必ず行ってください。ライセンスや貢献ガイドラインはリポジトリのルートにある LICENSE / CONTRIBUTING を参照してください。

---

必要であれば README にサンプル .env.example、より詳細な API 使用例、または各モジュールの API リファレンスを追加します。どの情報を優先して追記しますか？