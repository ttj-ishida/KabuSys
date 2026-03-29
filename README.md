# KabuSys — 日本株自動売買システム (README)

概要
----
KabuSys は日本株向けのデータプラットフォーム／アルゴリズム取引支援ライブラリです。J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）、ETL パイプライン、データ品質チェック、ニュース収集・NLP（OpenAI）による銘柄センチメント評価、さらに研究用のファクター計算や市場レジーム判定までを含むコンポーネント群を提供します。監査ログ（シグナル→発注→約定のトレーサビリティ）や DuckDB ベースの永続化を前提に設計されています。

主な機能
--------
- データ取得 / ETL
  - J-Quants API からの株価日足、財務データ、マーケットカレンダー取得（ページネーション対応）
  - 差分更新／バックフィル、取得データの DuckDB への冪等保存（ON CONFLICT）
- データ品質チェック
  - 欠損値・重複・スパイク（急変）・日付不整合の検出と QualityIssue レポート
- ニュース収集・前処理
  - RSS フィード収集（SSRF 対策、gzip 限度、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存
- AI（OpenAI）ベースの解析
  - 銘柄ごとのニュースセンチメント算出（news_nlp.score_news）
  - マクロ要因と ETF MA を統合した市場レジーム判定（regime_detector.score_regime）
  - API 呼び出しはリトライ／バックオフ設計でフェイルセーフにフォールバック
- 研究用ユーティリティ
  - ファクター計算（モメンタム / ボラティリティ / バリュー など）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー、Z スコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルの DDL、初期化ユーティリティ

必要条件（主な依存）
-------------------
- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- （標準ライブラリ：urllib, json, logging, datetime 等）

推奨インストール例:
- pip install duckdb openai defusedxml

セットアップ手順
----------------

1. リポジトリをクローン（またはパッケージを配置）
   - 例: git clone ...

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (macOS/Linux)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - pip install -e .            （プロジェクト配布用 setup/pyproject がある場合）
   - または最低限:
     - pip install duckdb openai defusedxml

4. 環境変数 / .env ファイルの準備
   - リポジトリルートに `.env` または `.env.local` を作成すると自動でロードされます
   - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
   - 必須の環境変数（config.Settings 参照）:
     - JQUANTS_REFRESH_TOKEN  — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD      — kabuステーション用パスワード（API 発注等）
     - SLACK_BOT_TOKEN        — Slack 通知用トークン（必要に応じて）
     - SLACK_CHANNEL_ID       — Slack チャンネル ID（必要に応じて）
     - OPENAI_API_KEY         — OpenAI API キー（news_nlp/regime_detector 実行時）
   - 任意／デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト INFO
     - DUCKDB_PATH, SQLITE_PATH — DB ファイルパス（デフォルト: data/kabusys.duckdb / data/monitoring.db）

例: .env（最小）
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    OPENAI_API_KEY=sk-...
    KABU_API_PASSWORD=your_kabu_password
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567

使い方（基本的な操作例）
-----------------------

- DuckDB 接続を作る（デフォルトの DB パスを使う例）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（run_daily_etl）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニュースのセンチメントスコア算出（OpenAI API 必須）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {n_written} symbols")
  ```

- 市場レジーム判定（ETF 1321 とマクロニュースの合成）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログスキーマ初期化（監査用 DB の作成）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn は初期化済みの DuckDB 接続
  ```

- 研究用ファクター計算（一例）
  ```python
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  mom = calc_momentum(conn, target_date=date(2026,3,20))
  vol = calc_volatility(conn, target_date=date(2026,3,20))
  val = calc_value(conn, target_date=date(2026,3,20))
  ```

運用上の注意
------------
- Look-ahead バイアス回避に設計されているため、関数は内部で datetime.today() を無闇に参照しないものが多く、必ず target_date を明示するワークフローを推奨します。
- OpenAI / J-Quants 等の外部 API 呼び出しは課金対象かつレート制限があります。API キーやリトライ設定は慎重に運用してください。
- ETL やニュース収集はネットワークや API の障害に対してフェイルセーフ設計（エラーでスキップしてログ出力）ですが、ログ監視とアラート設定を行ってください。
- DuckDB の executemany はバージョンにより空リストの挙動が異なるため、本プロジェクトでは空リストを送らない実装上の工夫があります。

ディレクトリ構成（主要ファイル）
-------------------------------
リポジトリの主要モジュール / ファイル（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理（.env 自動ロード機能）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（OpenAI）ロジック
    - regime_detector.py     — マーケットレジーム判定ロジック
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult の再エクスポート
    - news_collector.py      — RSS ニュース収集・前処理
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize 等）
    - audit.py               — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー等

開発・テスト
------------
- 自動ロードされる .env は開発時便利ですが、CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- OpenAI 呼び出し部分は内部で分離されているため、unittest.mock.patch を使って _call_openai_api をモックしやすく設計されています。
- DuckDB を使うため、テスト時は ":memory:" を DB パスに指定してインメモリ DB を利用できます（例: init_audit_db(":memory:")）。

ライセンス / 貢献
----------------
- 本ドキュメントはコードベースから抽出した情報に基づいています。実際のリポジトリに LICENSE / CONTRIBUTING ドキュメントがある場合はそちらに従ってください。

補足
----
- この README は提供されたソースコードを基に作成しています。追加の CLI、設定例、CI 設定、requirements.txt / pyproject.toml 等がある場合はそれらに合わせてセットアップ手順を補完してください。
- 質問や使い方の具体例（ETL チェーンのスケジュール化、Slack 通知連携、kabuステーション経由の発注フロー等）を希望される場合は、利用シナリオを教えてください。具体例を追加して案内します。