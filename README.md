README
======

プロジェクト概要
--------------
KabuSys は日本株のデータパイプライン、ニュースNLP、ファクター研究、および監査トレーサビリティを備えた自動売買／研究プラットフォームのコアライブラリ群です。  
主に DuckDB をデータストアに利用し、J-Quants API / RSS / OpenAI（LLM）などを組み合わせてデータ収集・品質チェック・AI スコアリング・市場レジーム判定・研究用統計処理を行います。

設計上のポイント
- Look-ahead bias（先見バイアス）対策が組み込まれており、date 引数ベースで処理することで将来情報利用を防止しています。
- ETL・保存処理は冪等性（idempotent）を考慮しており、ON CONFLICT / UPDATE を使って既存データを安全に更新します。
- 外部 API 呼び出し（J-Quants / OpenAI 等）にはレート制御・リトライ・フェイルセーフを組み込んでいます。
- データ品質チェック・監査ログ（発注〜約定のトレース）を含み、運用時の可観測性を確保します。

主な機能一覧
--------------
- データ取得 / ETL
  - J-Quants からの株価（日足）・財務データ・JPX カレンダー取得（pagination/リトライ/レート制御）
  - 差分更新・バックフィル対応の run_daily_etl（prices / financials / calendar）
- ニュース収集
  - RSS を正規化・前処理して raw_news テーブルへ保存（SSRF対策・gzip・サイズ制限等）
- ニュース NLP（AI）
  - 銘柄ごとのニュースセンチメントを OpenAI（gpt-4o-mini）でスコアリング（score_news）
  - マクロニュース＋ETF MA乖離から市場レジームを判定（score_regime）
- 研究ユーティリティ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）・ファクター統計サマリー
  - Zスコア正規化ユーティリティ
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合チェック（run_all_checks）
- 監査ログ
  - signal_events / order_requests / executions 等の監査テーブル作成・初期化（init_audit_schema / init_audit_db）

セットアップ手順
----------------
前提
- Python 3.10+（typing の一部構文などに依存）
- ネットワーク接続（J-Quants / OpenAI / RSS）

1. リポジトリをクローン
   - git clone <repo-url>
   - プロジェクトルートには .git または pyproject.toml が存在することを期待します（自動 .env ロードで使用）。

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 代表的なパッケージ:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※ プロジェクトに pyproject.toml / requirements.txt があればそれを使ってください:
   - pip install -e .
   - または pip install -r requirements.txt

4. 環境変数 / .env を設定
   - プロジェクトルートの .env（および機密管理したい場合は .env.local）に必要なキーを設定します。自動読み込みはデフォルトで有効です（後述）。

主要な環境変数（例）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=your_openai_api_key
- KABU_API_PASSWORD=your_kabu_api_password
- SLACK_BOT_TOKEN=your_slack_bot_token
- SLACK_CHANNEL_ID=your_slack_channel_id
- DUCKDB_PATH=data/kabusys.duckdb         （デフォルト）
- SQLITE_PATH=data/monitoring.db          （デフォルト）
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=INFO|DEBUG|...

.env 自動読み込みの挙動
- kabusys.config モジュールはプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を探索し、.env を読み込みます。
- 読み込み順: OS環境変数 > .env.local > .env（.env.local が .env を上書き）
- 自動読み込みを無効にする場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数にセットしてください（テスト時に便利）。

使い方（サンプル）
------------------

基本的な DuckDB 接続と ETL の実行例
- Python REPL やスクリプトで:

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  # DuckDB ファイル接続（デフォルトパスは settings.duckdb_path）
  conn = duckdb.connect(str(settings.duckdb_path))

  # 日次 ETL を実行（target_date を省略すると today が使われます）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

ニュースセンテンス分析（score_news）
- OpenAI API キーが環境変数 OPENAI_API_KEY に設定されている前提:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"ai_scores に書き込んだ銘柄数: {written}")

市場レジーム判定（score_regime）
- ETF（1321）200日 MA とマクロニュースを用いて日次レジームを判定します:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

監査ログ DB 初期化
- 監査ログ用 DuckDB を初期化して接続を取得する:

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # この conn に対して監査テーブルが作成されています

RSS ニュース取得（fetch_rss）
- ニュース収集のための単体関数:

  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])

設定値参照
- アプリ設定は kabusys.config.settings を通じて取得できます（環境変数チェック・バリデーションが実装されています）:

  from kabusys.config import settings
  print(settings.duckdb_path, settings.env, settings.is_live)

主要 API の注意点
- OpenAI 呼び出しは gpt-4o-mini（JSON Mode）を想定しており、API 料率やコストに注意してください。
- J-Quants の API 呼び出しはレート制御・トークン自動リフレッシュを行います。refresh token は JQUANTS_REFRESH_TOKEN に設定してください。
- ETL / AI 処理は外部通信を伴うため、テスト時は各種 HTTP 呼び出しや OpenAI 呼び出しをモックすることを推奨します（ソース内にモック用の差し替えを想定した設計あり）。

ディレクトリ構成（主要ファイル）
---------------------------------
src/kabusys/
- __init__.py
- config.py                  — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py              — ニュースセンチメントスコア（score_news）
  - regime_detector.py       — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py        — J-Quants API クライアント（fetch / save）
  - pipeline.py              — ETL パイプライン（run_daily_etl 等）
  - etl.py                   — ETL 結果クラス ETLResult の再輸出
  - calendar_management.py   — 市場カレンダー管理（is_trading_day 等）
  - news_collector.py        — RSS 収集・前処理
  - stats.py                 — zscore_normalize 等の統計ユーティリティ
  - quality.py               — データ品質チェック（run_all_checks 等）
  - audit.py                 — 監査ログ用スキーマ初期化
- research/
  - __init__.py
  - factor_research.py       — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py   — forward returns / IC / factor summary
- ai/, data/, research/ それぞれにテスト可能な単位関数が揃っています。

開発・運用上の注意
------------------
- テスト／開発環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動読み込みを抑止するとテストが安定します。
- OpenAI / J-Quants の呼び出しは料金やレート制限に注意して使用してください。大量 API 呼び出しはコストがかかります。
- ETL / AI スコアリングは外部依存のため、CI では HTTP クライアントや OpenAI をモックすることを推奨します。
- DuckDB の executemany に関する互換性（空リスト不可など）をコードが扱っています。ライブラリのバージョンに注意してください。

ライセンス / 貢献
-----------------
（リポジトリに LICENSE ファイルがあればそこを参照してください。特に指定がない場合はリポジトリ所有者に問い合わせてください。）

最後に
------
この README はコードベースの主要設計意図と使い方の概要をまとめたものです。詳細な実装や追加のユーティリティ（例: Slack 通知、kabu ステーション実行モジュール等）はソース内のドキュメンテーションコメントを参照してください。必要であれば、README にサンプル .env.example やデプロイ手順（systemd / cron / Airflow）を追記できます。