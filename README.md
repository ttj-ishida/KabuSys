KabuSys — 日本株自動売買 / データプラットフォーム
======================================

概要
----
KabuSys は日本株のデータ収集・品質管理・ファクター計算・ニュースNLP・市場レジーム判定・監査ログを含む
バックテスト / 自動売買プラットフォームのコアライブラリです。DuckDB を内部データストアに用い、
J-Quants API や外部 RSS / OpenAI（gpt-4o-mini）を利用した ETL と解析処理を提供します。

主な特徴
--------
- ETL パイプライン（株価日足、財務、マーケットカレンダー）の差分取得と冪等保存
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）とニュース本文の前処理（SSRF 対策、トラッキング除去）
- ニュース NLP（OpenAI）による銘柄ごとのセンチメントスコアリング（ai_scores テーブル）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM スコアを合成）
- 研究用ユーティリティ（ファクター計算・将来リターン・IC など）
- 監査ログ（signal_events, order_requests, executions）の初期化・管理
- 設定管理（.env の自動読み込み / 環境変数による構成）

前提条件
--------
- Python 3.10+ 推奨
- DuckDB
- OpenAI Python SDK（gpt 系モデル呼び出し）
- defusedxml（RSS パースの安全化）
- ネットワークアクセス（J-Quants API / RSS / OpenAI）

（実際の依存パッケージはプロジェクトの requirements.txt / pyproject.toml を参照してください）

インストール
------------
ソースを直接利用する場合（開発環境）:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

3. パッケージを開発モードでインストール（オプション）
   - pip install -e .

環境変数（必須 / 推奨）
-----------------------
最低限設定が必要な環境変数（例）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 投稿先チャンネル ID（必須）

その他（デフォルトあり）:

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）

.env の自動読み込み:
- プロジェクトルートに .env/.env.local を置くと自動で読み込まれます
- 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

セットアップ手順（例）
--------------------
1. DuckDB ファイル作成（任意）
   - data ディレクトリを作成: mkdir -p data
   - DuckDB 接続はコード内で作成します（例を参照）

2. 監査ログ用 DB 初期化（任意）
   - from kabusys.data.audit import init_audit_db
   - conn = init_audit_db("data/audit.duckdb")

3. .env を用意（.env.example を元に作成）
   例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=your_password
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

主な使い方（コード例）
---------------------

- DuckDB 接続の作成（例）
  from pathlib import Path
  import duckdb
  conn = duckdb.connect(str(Path("data/kabusys.duckdb")))

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアリング（OpenAI 必須）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {n_written} codes")

- 市場レジーム判定（OpenAI 必須）
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 監査スキーマ初期化
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

- ニュース RSS 取得（単体）
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")

注意点 / 設計方針（要約）
-----------------------
- ルックアヘッドバイアス対策: 各処理は target_date を明示的に受け取り、datetime.today()/date.today() を不必要に参照しないよう設計されています。
- 冪等性: J-Quants 取得結果・RSS 保存・audit テーブル作成などは冪等的に設計されています（ON CONFLICT / UUID を利用）。
- フェイルセーフ: API 呼び出し失敗時は処理を継続するようにし、致命的なエラーのみ上位に伝搬します（例: OpenAI API が失敗した場合はスコアを 0 にフォールバックする等）。
- セキュリティ: RSS の SSRF 対策、defusedxml の利用、URL 正規化・トラッキング除去などが組み込まれています。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py                 — パッケージ初期化、バージョン
- config.py                   — 環境変数 / .env 読み込み・Settings
- ai/
  - __init__.py
  - news_nlp.py                — ニュースセンチメント（score_news 等）
  - regime_detector.py         — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py     — マーケットカレンダー管理・営業日判定
  - etl.py                     — ETL 結果型のエクスポート
  - pipeline.py                — ETL パイプライン（run_daily_etl 等）
  - stats.py                   — 汎用統計（zscore_normalize）
  - quality.py                 — データ品質チェック
  - audit.py                   — 監査ログテーブル作成 / init_audit_db
  - jquants_client.py          — J-Quants API クライアント（取得 / 保存）
  - news_collector.py          — RSS 収集・前処理
- research/
  - __init__.py
  - factor_research.py         — ファクター計算（momentum / value / volatility）
  - feature_exploration.py     — 将来リターン / IC / 統計サマリー
- research/...                 — 研究用ユーティリティの公開
- その他モジュール             — strategy / execution / monitoring（パッケージ公開名に含まれるがここでは一部を抜粋）

付録: よくある操作例
-------------------
- 自動 ETL を cron や Airflow 等で日次実行する:
  - 仮想環境を有効化し、Python スクリプトで run_daily_etl を呼ぶ
- OpenAI 呼び出しテスト:
  - 環境変数 OPENAI_API_KEY を一時的に設定し、score_news / score_regime を呼ぶ
- デバッグ:
  - LOG_LEVEL=DEBUG を設定して詳細ログを出力

サポート・拡張
--------------
- 新しい RSS ソースは data.news_collector.DEFAULT_RSS_SOURCES に追加してください
- OpenAI モデルやプロンプトは ai/news_nlp.py / ai/regime_detector.py 内で調整可能です
- DuckDB スキーマの変更は data.audit.init_audit_schema 等の実装を参考に行ってください

最後に
------
README はコードベースの要点をまとめたものです。詳細な API や運用手順は各モジュール（特に data.pipeline, data.jquants_client, ai.news_nlp, ai.regime_detector, data.audit）内の docstring を参照してください。必要であれば README に追加したい実行例や運用ガイド（cron / systemd / Docker Compose 等）を教えてください。