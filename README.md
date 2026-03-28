KabuSys
======

概要
----
KabuSys は日本株向けのデータ基盤・リサーチ・AI 評価・監査ログを備えた自動売買補助ライブラリです。  
主に以下を目的としています：

- J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）
- DuckDB ベースの ETL パイプラインとデータ品質チェック
- ニュースの NLP（LLM）による銘柄センチメント算出
- 市場レジーム判定（ETF + マクロニュース）
- 監査用テーブル（signal → order → execution のトレーサビリティ）
- 研究用ファクター計算・特徴量探索ユーティリティ

機能一覧
--------
主な機能は以下の通りです。

- data
  - J-Quants API クライアント（取得/保存/ページネーション/認証リフレッシュ）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理・営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - ニュース収集（RSS、SSRF 対策、正規化、raw_news への保存ロジック準備）
  - データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - 監査ログ（signal_events / order_requests / executions）の初期化ユーティリティ
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュースを LLM で評価して銘柄ごとのスコアを ai_scores に書き込む（score_news）
  - ETF（1321）の MA とマクロニュースの LLM センチメントを合成して市場レジームを判定（score_regime）
- research
  - ファクター計算（momentum / value / volatility 等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

前提（依存）
------------
主な依存項目（開発時点）：

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他標準ライブラリ

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone ...（プロジェクトルートには .git または pyproject.toml があることが望ましい）

2. パッケージをインストール（仮想環境推奨）
   - pip install -e .   （もしくは必要な依存を個別に pip install duckdb openai defusedxml など）

3. 環境変数設定
   - プロジェクトルートに .env を作成することで、自動的に読み込まれます（読み込み順: OS環境変数 > .env.local > .env）。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（必須/任意）
- 必須（実行する機能に依存）
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（get_id_token で使用）
  - OPENAI_API_KEY : OpenAI 呼び出しを行う場合に必要（score_news / score_regime 等）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : Slack 通知を使う場合
  - KABU_API_PASSWORD : kabuステーション API を使う場合
- データベースパス（任意、デフォルト値あり）
  - DUCKDB_PATH : デフォルト "data/kabusys.duckdb"
  - SQLITE_PATH : デフォルト "data/monitoring.db"
- 実行環境設定
  - KABUSYS_ENV : development / paper_trading / live（デフォルト development）
  - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL

注意:
- config モジュールは .env ファイルのパースを細かく実装しており、export KEY=val 形式やクォート/コメントを適切に扱います。

使い方（主要な例）
-----------------

以下は Python から直接呼び出す例です。DuckDB 接続は duckdb.connect(...) を渡します。

- ETL（デイリーパイプライン）を実行する

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアリング（score_news）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"written: {n_written}")

- 市場レジーム判定（score_regime）

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 監査スキーマ初期化（監査用 DB 作成）

  from pathlib import Path
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db(Path("data/audit.duckdb"))
  # conn は duckdb 接続。init_audit_schema は既に実行済み。

- 市場カレンダー・営業日判定

  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))

実装上の注意点
- Look-ahead バイアス回避のため、各モジュールは datetime.today()/date.today() を直接参照しないよう設計されています（target_date を明示的に渡すことが推奨）。
- OpenAI 呼び出しはリトライ・タイムアウト等ハンドリング済みですが、APIキーは呼び出し側で渡すか環境変数 OPENAI_API_KEY を設定してください。
- J-Quants API 呼び出しはレート制限と再試行、401 の自動リフレッシュ処理を備えています。

ディレクトリ構成
----------------

主要ファイル（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                    # 環境変数読み込み・settings
  - ai/
    - __init__.py
    - news_nlp.py                # ニュースから銘柄スコア算出（score_news）
    - regime_detector.py         # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          # J-Quants API クライアント（fetch/save）
    - pipeline.py                # ETL 実行エントリ（run_daily_etl 等）
    - etl.py                     # ETLResult の再エクスポート
    - calendar_management.py     # 市場カレンダー管理・営業日判定
    - news_collector.py          # RSS 取得 / 前処理ユーティリティ
    - quality.py                 # データ品質チェック
    - stats.py                   # 統計ユーティリティ（zscore_normalize）
    - audit.py                   # 監査ログスキーマ初期化
    - ...（その他補助モジュール）
  - research/
    - __init__.py
    - factor_research.py         # ファクター計算（momentum/value/volatility）
    - feature_exploration.py     # 将来リターン / IC / 統計サマリ
  - execution/                    # 発注・ブローカー連携（将来的な配置想定）
  - monitoring/                   # 監視・メトリクス収集（将来的な配置想定）

補足・開発メモ
---------------
- .env の自動読み込みは、config._find_project_root() が .git または pyproject.toml を検出して行われます。CI やテストで自動読み込みを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_collector には SSRF / gzip bomb / XML bomb に対する多段防護が組み込まれています（defusedxml 使用、Content-Length チェック、受信上限など）。
- DuckDB への書き込みは冪等性（ON CONFLICT 句）を意識して実装されています。

サポート / 貢献
----------------
バグ報告や機能提案はリポジトリの Issues にお願いします。Pull Request は歓迎です。

以上。