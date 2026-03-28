# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュース NLP（LLM ベース）・市場レジーム判定・監査ログ（監査テーブルの初期化）など、取引システムに必要な基盤機能を提供します。

---

## 主な機能

- データ取得 / ETL
  - J-Quants API から株価日足、財務データ、JPX カレンダーを差分取得・保存（DuckDB）
  - 差分取得・バックフィル・ページネーション対応・レートリミット／リトライ実装
- データ品質チェック
  - 欠損、重複、スパイク（急騰/急落）、日付不整合の検出と報告
- ニュース収集 & 前処理
  - RSS 取得（SSRF 対策、トラッキングパラメータ除去、サイズ上限など）
  - raw_news への冪等保存、news_symbols との紐付け（記事と銘柄）
- ニュース NLP（LLM 統合）
  - 銘柄ごとのニュースを LLM（gpt-4o-mini）に投げてセンチメント（ai_score）を算出・保存
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 と LLM 結果の合成）
  - JSON Mode / 再試行・フォールバック実装（API失敗時はゼロフォールバック）
- 研究（Research）ユーティリティ
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計
- 監査ログ（Audit）
  - signal_events / order_requests / executions などの監査テーブル定義と初期化ユーティリティ
  - 監査DB（独立 DuckDB）初期化関数を提供

---

## 要求環境（推奨）

- Python 3.10+
- 必要なパッケージ（一例）
  - duckdb
  - openai
  - defusedxml
  - そのほか標準ライブラリ（urllib 等）

例:
pip install duckdb openai defusedxml

（実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをチェックアウト／インストール
   - 開発時（editable install）:
     - pip install -e .
   - もしくは個別に依存をインストール:
     - pip install duckdb openai defusedxml

2. 環境変数を準備
   - プロジェクトルートに `.env` / `.env.local` を置くことで自動読み込みされます（優先度: OS env > .env.local > .env）。
   - 自動ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定
   - 必須の環境変数（主なもの）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
     - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector が使用）
   - 任意 / デフォルト
     - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

3. DB 初期化（監査ログ）
   - 監査用 DuckDB を初期化する例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
   - 既存接続に監査スキーマを追加する場合:
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)

---

## 使い方（簡易サンプル）

以下は主要な機能を Python から呼ぶ最小例です。すべての操作は DuckDB 接続を渡して行います。

- 共通: DuckDB 接続
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントスコア算出（LLM）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数で指定
  print(f"書き込み銘柄数: {n}")

- 市場レジーム判定（MA200 + マクロニュース LLM）
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY 必須

- ETL の個別ジョブ（価格のみなど）
  from kabusys.data.pipeline import run_prices_etl
  from datetime import date
  fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
  print(f"fetched={fetched}, saved={saved}")

- 監査DB 初期化（例）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブルが作成されます

---

## 設計上の注意点・挙動

- Look-ahead bias の排除
  - バックテストやスコアリングでの将来参照を防ぐため、内部関数は date 引数に基づく時刻ウィンドウを使い、date.today() を不要に参照しない設計となっています（例: news のウィンドウ計算、MA 計算）。
- .env の読み込み
  - パッケージは起動時にプロジェクトルート（.git または pyproject.toml を検索）を基準に .env/.env.local を自動読み込みします。
  - OS 環境変数は上書きされません（.env.local は override=True で上書き可。ただし OS 環境は protected）。
- OpenAI / J-Quants の取り扱い
  - OpenAI 呼び出しは JSON mode を前提にレスポンス構造を厳密にチェックします。API エラーや JSON パース失敗時はフェイルセーフとしてゼロ評価（0.0）を返すか、そのチャンクをスキップします。
  - J-Quants クライアントはレートリミット（120 req/min）を尊重する RateLimiter・リトライ・401 時のトークン自動リフレッシュを実装しています。
- DuckDB への書き込みは冪等性を重視（ON CONFLICT DO UPDATE / INSERT ... DO NOTHING 等）しています。
- ニュース取得は SSRF 対策、サイズチェック、gzip 対応、XML パースの安全化（defusedxml）などを実装しています。

---

## 主要ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py  — 環境変数 / 設定の読み込みと検証
- ai/
  - __init__.py
  - news_nlp.py        — ニュースを LLM でスコアリングして ai_scores に保存
  - regime_detector.py — MA200 とマクロニュース LLM を合成して market_regime に保存
- data/
  - __init__.py
  - calendar_management.py — JPX カレンダー管理・営業日判定
  - pipeline.py            — ETL パイプラインとジョブ（run_daily_etl 等）
  - jquants_client.py      — J-Quants API クライアント（取得 / 保存関数）
  - news_collector.py      — RSS 取得 / 前処理 / raw_news 保存
  - quality.py             — データ品質チェック
  - stats.py               — z-score 等の統計ユーティリティ
  - audit.py               — 監査ログテーブル定義 & 初期化
  - etl.py                 — ETLResult の公開
- research/
  - __init__.py
  - factor_research.py     — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン / IC / サマリー 等
- research/...（他モジュール）
- その他（strategy, execution, monitoring といったサブパッケージ用のエントリは __all__ に定義されているが、実装はプロジェクトに応じて拡張）

---

## 環境変数一覧（抜粋）

必須（最低限）：
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- OPENAI_API_KEY（news_nlp / regime_detector を使う場合）

任意／デフォルト有り：
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL — default: INFO
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を指定すると .env 自動読み込みを無効化

.env ファイルはコメントや export KEY=val 形式にも対応し、クォートやエスケープにも配慮したパーサーで読み込まれます。

---

## ロギング／監視

- 各モジュールは標準 logging を使用しています。LOG_LEVEL 環境変数で制御してください。
- ETL 結果は ETLResult オブジェクトで返され、詳細な品質チェック結果やエラー情報を含みます。

---

不明点や追加の使用シナリオ（例えば strategy 層や execution 層の統合方法）についてのドキュメントが必要であれば、目的に合わせたサンプルコードや設計ドキュメントを作成します。どの部分の詳細が欲しいか教えてください。