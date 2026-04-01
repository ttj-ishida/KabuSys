KabuSys
=======

概要
----
KabuSys は日本株向けのデータ基盤・リサーチ・AI スコアリング・監査ログ・ETL を備えた自動売買/リサーチ用ライブラリ群です。  
主に以下を提供します。

- J-Quants API からの差分 ETL（株価・財務・マーケットカレンダー）の実装と品質チェック
- ニュース収集（RSS）と OpenAI を用いたニュースセンチメント（銘柄別 ai_score）算出
- 市場レジーム判定（ETF MA とマクロニュースを合成）
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- 監査ログ（signal → order_request → execution）用の DuckDB スキーマ初期化・操作ユーティリティ
- 環境変数ベースの設定管理（.env 自動読み込み対応）

主な設計方針は「ルックアヘッドバイアスの排除」「ETL の冪等性」「外部 API の堅牢なリトライ/レート制御」「テスト容易性」です。

機能一覧
--------
主なモジュールと機能（抜粋）：

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）と Settings（JQUANTS_REFRESH_TOKEN 等のアクセス）
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能
- kabusys.data
  - jquants_client: J-Quants API 呼び出し / DuckDB 保存（差分取得、ページネーション、リトライ、レート制御）
  - pipeline: run_daily_etl による日次 ETL（calendar/prices/financials + 品質チェック）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector: RSS 収集と前処理（SSRF 対策、サイズ制限、トラッキングパラメータ除去）
  - audit: 監査ログテーブル DDL と init_audit_db（DuckDB 初期化）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - stats: zscore_normalize 等の汎用統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄毎のニュースを集約して OpenAI に投げ、ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して market_regime を保存
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

セットアップ手順
----------------

前提
- Python 3.10 以上（typing の | 記法および from __future__ annotations を使用）
- DuckDB、OpenAI SDK、defusedxml 等が必要

推奨パッケージ（例）
- duckdb
- openai
- defusedxml

例: 仮想環境の作成とパッケージインストール
- Unix/macOS:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install --upgrade pip
  - pip install duckdb openai defusedxml

requirements.txt（例）
- duckdb
- openai
- defusedxml

環境変数 / .env
必須（少なくとも以下を設定してください）:
- JQUANTS_REFRESH_TOKEN (J-Quants リフレッシュトークン)
- KABU_API_PASSWORD (kabu ステーション API 用パスワード、必要に応じて)
- SLACK_BOT_TOKEN (Slack 通知を使う場合)
- SLACK_CHANNEL_ID (Slack 通知を使う場合)

その他（デフォルト有り）:
- KABUSYS_ENV (development | paper_trading | live) デフォルト: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) デフォルト: INFO
- DUCKDB_PATH デフォルト: data/kabusys.duckdb
- SQLITE_PATH デフォルト: data/monitoring.db
- PID_FILE_PATH デフォルト: data/execution.pid

プロジェクトルートに .env/.env.local を配置すると、kabusys.config が自動で読み込みます（CWD ではなくパッケージ位置から .git または pyproject.toml を辿ってプロジェクトルートを探します）。自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（簡易ガイド）
-------------------

DuckDB 接続の作り方（例）:
- import duckdb
- conn = duckdb.connect("data/kabusys.duckdb")

ETL（日次）を実行する（Python から）:
- from datetime import date
- from kabusys.data.pipeline import run_daily_etl
- import duckdb
- conn = duckdb.connect("data/kabusys.duckdb")
- result = run_daily_etl(conn, target_date=date(2026, 3, 20))
- print(result.to_dict())

ニューススコアリング（OpenAI 必須）:
- from datetime import date
- import duckdb
- from kabusys.ai.news_nlp import score_news
- conn = duckdb.connect("data/kabusys.duckdb")
- n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
- print(f"書き込み銘柄数: {n_written}")

市場レジーム判定:
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

監査ログ DB 初期化:
- from kabusys.data.audit import init_audit_db
- conn_audit = init_audit_db("data/audit.duckdb")
- # conn_audit を使用して監査テーブルへ書き込み・検索が可能

ETLResult の確認:
- ETL の戻り値は kabusys.data.pipeline.ETLResult（to_dict() で詳細を取得）

注意点 / 運用上のヒント
- OpenAI 呼び出し、J-Quants API 呼び出しには適切な API キーが必要です（環境変数または関数引数で渡す）。
- run_daily_etl は複数ステップ（calendar → prices → financials → quality check）。一部ステップが失敗しても他が継続され、ETLResult.errors に記録されます。
- DuckDB の executemany で空リストを渡すと不具合が出るバージョンがあるため、コード内で空リストチェックをしています。自作コードでも注意してください。
- news_collector は RSS フィードのリダイレクト検査やプライベートIPチェック（SSRF 対策）を行います。RSS URL は http/https のみ許可されます。

ディレクトリ構成
----------------
（主要ファイル・モジュールのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - etl.py
      - quality.py
      - stats.py
      - calendar_management.py
      - news_collector.py
      - audit.py
      - audit (DB 初期化ユーティリティ)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research (その他の分析ユーティリティ群)
    - ai (LLM を利用する処理群)
    - config.py (環境設定管理)

主な公開 API（例）
- kabusys.config.settings — 環境設定アクセス
- kabusys.data.pipeline.run_daily_etl — 日次 ETL 実行（ETLResult を返す）
- kabusys.data.jquants_client.* — J-Quants 取得 / 保存ユーティリティ
- kabusys.data.news_collector.fetch_rss — RSS 取得ユーティリティ
- kabusys.ai.news_nlp.score_news — ニュースセンチメント算出・ai_scores 書込
- kabusys.ai.regime_detector.score_regime — 市場レジーム判定・書込
- kabusys.data.audit.init_audit_db / init_audit_schema — 監査ログ初期化

ライセンス・貢献
----------------
この README はコードベースから生成されています。実際のライセンス表記や貢献ガイド（CONTRIBUTING.md）がプロジェクトルートにあればそちらを参照してください。

問い合わせ / 追加情報
--------------------
- 本リポジトリに関する技術的な質問や仕様の補足が必要であれば、どの箇所について知りたいかを指定して質問してください。README のサンプルコード・運用手順などを追加で用意します。