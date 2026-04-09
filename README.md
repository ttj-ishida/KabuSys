# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）→ ETL → 品質チェック → 特徴量計算 → 戦略 / 発注 / 監査ログまでのワークフローを想定したモジュール群を提供します。AI を用いたニュースセンチメント評価や市場レジーム判定も含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からの株価・財務・市場カレンダー取得と DuckDB への冪等保存
- RSS ベースのニュース収集と記事の前処理・保存
- OpenAI を用いたニュースセンチメント（銘柄別）およびマクロセンチメント（市場レジーム）スコアリング
- ETL パイプラインの統合（差分取得・バックフィル・品質チェック）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計サマリー）
- 発注・約定の監査ログ（冪等性とトレーサビリティ）
- 簡易的な設定管理（環境変数 / .env の自動読み込み）

設計方針としては、Look-ahead バイアス防止や冪等性、外部 API のリトライ・レート制御、DuckDB を中心としたローカル永続化を重視しています。

---

## 主な機能一覧

- data/jquants_client
  - J-Quants API との通信（token refresh、ページネーション、レート制限、リトライ）
  - fetch/save の冪等実装（raw_prices, raw_financials, market_calendar 等）
- data/pipeline
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック を順に実行
  - ETLResult により結果・品質問題を集約
- data/news_collector
  - RSS フィード取得、SSRF 対策、URL 正規化、記事ID生成、raw_news への冪等保存
- data/quality
  - 欠損、スパイク、重複、日付不整合などの品質チェック（QualityIssue データクラス）
- data/calendar_management
  - market_calendar を使った営業日判定・前後営業日の取得などのユーティリティ
- data/audit
  - signal / order_requests / executions の監査ログスキーマ定義と初期化（監査DB初期化関数あり）
- data/stats
  - zscore_normalize 等の汎用統計ユーティリティ
- ai/news_nlp
  - 銘柄ごとのニュースをまとめて OpenAI に投げ、ai_scores テーブルへスコア書き込み（score_news）
- ai/regime_detector
  - ETF(1321) の 200日MA 乖離とマクロニュースの LLM センチメントを合成して市場レジーム判定（score_regime）
- research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

パッケージは strategy / execution / monitoring といった上位層のエクスポートを想定しています（kabusys.__init__ の __all__ に含まれます）。

---

## 必要条件

- Python 3.10+
  - 型注釈（| 演算子）を使用しているため Python 3.10 以上を推奨します。
- 外部ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - （その他 urllib 等は標準ライブラリで賄われます）
- J-Quants アカウント（リフレッシュトークン）
- OpenAI API キー（ニュース/レジーム判定を使う場合）

依存パッケージはプロジェクトの requirements.txt / pyproject.toml に従ってください。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト

   git clone <repo-url>
   cd <repo>

2. 仮想環境作成（例）

   python -m venv .venv
   source .venv/bin/activate

3. 依存パッケージをインストール

   pip install -r requirements.txt

   （requirements.txt が無い場合は少なくとも duckdb / openai / defusedxml 等をインストールしてください）

4. 環境変数設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成すると、自動的に読み込まれます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   代表的な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定（任意）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - PAPER_FILL_MODE: paper trading の fill モード（instant|partial|never|reject、デフォルト: instant）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 監視系の設定
   - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
   - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

5. データディレクトリ作成

   デフォルトでは `data/` 以下に DuckDB や SQLite を置きます。必要に応じて作成してください。

---

## 使い方（代表例）

以下は主要な API の利用イメージです。実行は Python スクリプト / ジュピター / CLI ラッパーから行ってください。

- DuckDB 接続を作る

  from pathlib import Path
  import duckdb
  conn = duckdb.connect(str(Path("data/kabusys.duckdb")))

- 日次 ETL 実行

  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())

- ニュースセンチメント（銘柄別）をスコア化して ai_scores に書き込む

  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
  print("written:", n_written)

- 市場レジーム判定（regime）を実行

  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")

- J-Quants クライアントを直接使う

  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes
  token = get_id_token()  # settings.jquants_refresh_token を使用
  records = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))
  saved = save_daily_quotes(conn, records)

- 監査ログスキーマ初期化 / 専用監査DB作成

  from kabusys.data.audit import init_audit_db, init_audit_schema
  audit_conn = init_audit_db("data/audit.duckdb")  # ファイル作成・DDL 実行
  # 既存 conn に対して transactional に初期化する場合:
  # init_audit_schema(conn, transactional=True)

- ニュース収集（RSS）

  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  # 取得した記事を加工して DB に保存する処理はプロジェクトの ETL フローに合わせて実装してください。

- 研究用ユーティリティ（ファクター計算）

  from kabusys.research import calc_momentum, calc_value, calc_volatility
  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))

注意点:
- AI 機能は OpenAI の API（gpt-4o-mini を想定）を使用します。API 呼び出しはレスポンス検証やリトライロジックを含みますが、API キーが必要です。
- ETL / API 呼び出しは外部ネットワークや認証情報を扱うため、本番環境では適切なシークレット管理を行ってください。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。CI/テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って無効化できます。

---

## ディレクトリ構成（該当コード抜粋）

src/
  kabusys/
    __init__.py                # パッケージエントリ（__all__ 定義）
    config.py                  # 環境変数 / .env 読み込み・Settings クラス
    ai/
      __init__.py
      news_nlp.py              # 銘柄別ニューススコアリング（score_news）
      regime_detector.py       # 市場レジーム判定（score_regime）
    data/
      __init__.py
      jquants_client.py        # J-Quants API クライアント（fetch/save/get_id_token）
      pipeline.py              # ETL パイプライン（run_daily_etl 等）
      etl.py                   # ETL 型の再エクスポート（ETLResult）
      stats.py                 # 統計ユーティリティ（zscore_normalize）
      quality.py               # 品質チェック（QualityIssue, run_all_checks）
      calendar_management.py   # マーケットカレンダー関連ユーティリティ
      news_collector.py        # RSS ニュース取得・前処理
      audit.py                 # 監査ログテーブル定義・初期化
    research/
      __init__.py
      factor_research.py       # calc_momentum, calc_value, calc_volatility
      feature_exploration.py   # calc_forward_returns, calc_ic, factor_summary, rank
    # strategy/, execution/, monitoring/ 等上位層は __all__ に含まれているが、
    # 実装は別ファイル・将来追加を想定

各モジュールには docstring と設計方針（Look-ahead バイアス回避、冪等性、リトライ方針 等）が記載されています。実運用ではこれらの設計意図に従って利用してください。

---

## 注意事項 / ベストプラクティス

- OpenAI / J-Quants などの外部 API キーは環境変数で管理し、コードにハードコーディングしないでください。
- ETL 実行時は ETLResult の quality_issues と errors を確認し、重大な品質エラーがあれば適切に対処してください。
- DuckDB のファイルはバックアップを取るか、必要に応じて別領域に保管してください。
- news_collector は SSRF 対策や受信サイズ制限など安全対策を組み込んでいますが、追加の運用ルール（接続先のホワイトリスト等）を検討してください。
- テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、必要な設定をテスト側で注入してください。

---

もし README に追記したいサンプルスクリプトや CLI ラッパー、あるいは具体的な .env.example のテンプレートなどがあれば、それに合わせて README を拡張します。どの情報を優先的に追加しますか？