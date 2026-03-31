KabuSys — 日本株自動売買プラットフォーム（README）
=================================

概要
----
KabuSys は日本株のデータ取得・品質チェック・特徴量生成・ニュース NLP（LLM）によるセンチメント評価・市場レジーム判定・監査ログ管理などを含む、研究→本番までを想定したデータ基盤／リサーチ／一部売買ロジック用ユーティリティ群です。  
DuckDB をローカル DB として用い、J-Quants API や RSS、OpenAI（gpt-4o-mini）を利用するモジュール群を備えます。

主な機能
--------
- データETL（J-Quants API）: 株価日足、財務データ、JPXカレンダーの差分取得と DuckDB への冪等保存
- データ品質チェック: 欠損・スパイク・重複・日付不整合の検出
- ニュース収集: RSS からの収集、前処理、raw_news 保存（SSRF対策、トラッキング除去）
- ニュース NLP: OpenAI を用いた銘柄ごとのセンチメント算出（ai_scores への保存）
- 市場レジーム判定: ETF（1321）のMA乖離＋マクロニュースセンチメントを合成して日次レジーム判定
- 研究用ユーティリティ: ファクター計算（モメンタム／ボラティリティ／バリュー等）、将来リターン、IC 計算、Z スコア正規化
- 監査ログ（audit）: シグナル→発注→約定のトレーサビリティ用テーブル定義・初期化ユーティリティ
- 設定管理: .env / OS 環境変数からの設定読み込み（自動ロード機構付き）

動作要件（想定）
----------------
- Python 3.10+（型記法に Union | を使用）
- ライブラリ（主要な例）
  - duckdb
  - openai (または openai SDK の互換 API を提供するパッケージ)
  - defusedxml
  - その他標準ライブラリ（urllib, json, logging 等）
- ネットワークアクセス（J-Quants API、OpenAI API、RSS ソース）

セットアップ手順
---------------
1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix)
   - .venv\Scripts\activate     (Windows)

2. 必要パッケージをインストール
   - プロジェクトに requirements.txt があればその通りにインストールしてください。
   - 代表例:
     - pip install duckdb openai defusedxml

3. パッケージのインストール（開発モード）
   - プロジェクトルートで:
     - pip install -e .

4. 環境変数設定
   - ルートに .env または .env.local を置くと自動でロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。
   - 最低限設定が必要なキー（コード内参照）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY — OpenAI API キー（score_news / regime_detector で使用）
     - KABU_API_PASSWORD — kabuステーション API パスワード（実運用時）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知に使用する場合
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視/モニタリング用 SQLite（デフォルト data/monitoring.db）
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/...
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

初期 DB の準備（監査ログなど）
------------------------------
- 監査ログ用 DuckDB を初期化する例:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は duckdb.DuckDBPyConnection

- プロジェクトで使用する DuckDB 接続例:
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

主な使い方（サンプル）
---------------------

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニュースのセンチメントスコアを計算して ai_scores に保存
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026,3,20))
  print(f"wrote scores for {written} codes")

- 市場レジーム判定（1321 + マクロニュース）
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))  # OpenAI API キーは環境変数または api_key 引数で指定

- 研究用ファクター計算例
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))

- 設定の参照
  from kabusys.config import settings
  print(settings.duckdb_path, settings.is_live)

注意・トラブルシューティング
----------------------------
- OpenAI キー未設定時:
  - score_news / score_regime は ValueError を送出します。環境変数 OPENAI_API_KEY または関数の api_key 引数を設定してください。
- J-Quants トークン未設定:
  - jquants_client.get_id_token() は settings.jquants_refresh_token を参照し、未設定の場合は例外を投げます。
- .env 自動ロード:
  - settings モジュールはプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動ロードします。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB executemany の注意:
  - 一部関数（ai/news_nlp など）は DuckDB の executemany の仕様（空リスト不可）を考慮しています。API 実行結果が空のときは書き込みをスキップします。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                       — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                    — ニュース NLP（OpenAI）→ ai_scores 書き込み
  - regime_detector.py             — 市場レジーム判定（1321 MA + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py              — J-Quants API クライアント、保存処理
  - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
  - etl.py                         — ETLResult エクスポート
  - calendar_management.py         — 市場カレンダー管理・営業日判定等
  - stats.py                       — zscore_normalize 等の統計ユーティリティ
  - quality.py                     — データ品質チェック
  - audit.py                       — 監査ログテーブル定義 / 初期化
  - news_collector.py              — RSS 収集・前処理
- research/
  - __init__.py
  - factor_research.py             — momentum / volatility / value 等
  - feature_exploration.py         — forward returns / IC / summary / rank
- research/...                      — （上と同様）

ライセンス・貢献
----------------
- 本 README はコードベースに基づく簡易ドキュメントです。実際のライセンスやコントリビューション手順はリポジトリの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

補足
----
- 本 README はソース内の docstring とコードから機能と使い方を抜粋したものです。実運用時は .env.example（リポジトリに含む想定）やテストスイート、CI 設定を参照してください。質問や追加のドキュメント化を希望される場合は、どの箇所を詳しく説明するか教えてください。