KabuSys — 日本株自動売買システム（README）
=====================================

概要
----
KabuSys は日本株向けのデータプラットフォーム／自動売買基盤のライブラリ群です。  
主に次の役割を持ちます。

- J-Quants API からのデータ取得（株価日足・財務・市場カレンダー）
- ETL（差分取得・保存・品質チェック）の実行
- RSS ベースのニュース収集と LLM を使ったニュースセンチメント評価
- 市場レジーム判定（ETF の MA とマクロニュースの LLM 判定を合成）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用テーブル初期化
- リサーチ用ファクター計算・特徴量解析ユーティリティ

この README はコードベース（src/kabusys 以下）に基づく利用方法・セットアップをまとめたものです。

主な機能
--------
- data.jquants_client
  - J-Quants API からの取得（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / fetch_listed_info）
  - DuckDB への冪等保存（save_daily_quotes, save_financial_statements, save_market_calendar）
  - 認証トークン管理（get_id_token）とレート制御・リトライ実装

- data.pipeline
  - 日次 ETL パイプライン run_daily_etl：市場カレンダー → 株価 → 財務 → 品質チェック の順で処理
  - 個別ジョブ run_prices_etl / run_financials_etl / run_calendar_etl
  - ETL 結果を表す ETLResult

- data.news_collector
  - RSS フィード取得、前処理、raw_news テーブルへの冪等保存
  - SSRF 回避、圧縮・サイズ上限・XML の安全パースなどの保護機能

- ai.news_nlp
  - raw_news と news_symbols を使い、OpenAI（gpt-4o-mini）で銘柄ごとのニュースセンチメントを算出して ai_scores へ書込み（score_news）

- ai.regime_detector
  - ETF 1321 の 200 日 MA 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して市場レジーム（bull/neutral/bear）を判定して market_regime に保存（score_regime）

- data.quality
  - 欠損・重複・スパイク・日付不整合などの品質チェック（run_all_checks）

- data.audit
  - 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - シグナル／発注／約定をトレースするテーブル定義・インデックス

- data.stats / research.*
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）、Z スコア正規化、将来リターン、IC 計算、統計サマリー等（バックテスト／リサーチ用途）

セットアップ手順
----------------

前提
- Python 3.10 以上（PEP 604 の型記法（X | None）などを使用）
- システムにネットワークアクセス（J-Quants / OpenAI / RSS）できること

1. リポジトリを取得
   - 例: git clone ... （プロジェクトルートに .git または pyproject.toml があることを想定）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要な代表的パッケージ:
     - duckdb
     - openai
     - defusedxml
   - 例（pip）:
     - pip install duckdb openai defusedxml

   ※ 実際のプロジェクトでは pyproject.toml / requirements.txt に依存が定義されていることが想定されます。存在する場合は pip install -e . や pip install -r requirements.txt を使用してください。

4. 環境変数（.env）を作成
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（パッケージ import 時に自動ロード、無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi  (任意)
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb  (デフォルト)
     - SQLITE_PATH=data/monitoring.db    (デフォルト)
     - OPENAI_API_KEY=...  (AI 機能利用時に必要)
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...
   - .env のパースはシェル風の export / クォート / コメントをサポートしています。

使い方（代表的な例）
-------------------

以下は簡単な Python スニペット例です。実行前に必要な環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）を設定してください。

1) DuckDB 接続の準備
- settings.duckdb_path を使うとユーザ設定に従えます:

  from datetime import date
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL を実行する（全体パイプライン）
- run_daily_etl は市場カレンダー取得 → 株価 → 財務 → 品質チェック を実行します。

  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

3) ニュースセンチメント（銘柄ごと）を計算して ai_scores に書き込む
- OpenAI API キーは env か api_key 引数で与えます

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20))
  print(f"wrote {n_written} ai_scores")

4) 市場レジーム判定を行う（score_regime）
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))

5) 監査ログ用 DB の初期化
- 監査ログ専用の DuckDB ファイルを作ってスキーマを作成します

  from kabusys.data.audit import init_audit_db

  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit は初期化済みの DuckDB 接続

6) J-Quants から手動で株価を取得・保存する（低レベルAPI）
  from kabusys.data import jquants_client as jq
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
  jq.save_daily_quotes(conn, records)

注意点 / 実装上の方針
-------------------
- ルックアヘッドバイアス防止: 各モジュール（news_nlp, regime_detector, pipeline 等）は date.today()/datetime.today() を内部で直接参照しない設計になっており、target_date を呼び出し側が明示して与える想定です。
- 自動 .env 読み込み: パッケージ初回 import 時にプロジェクトルート（.git または pyproject.toml を探索）から .env/.env.local を自動で読み込みます。テストや特殊状況では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- OpenAI 呼び出し: リトライ・バックオフ等のフェイルセーフを備えています。API エラー時は例外を投げずに 0 や空リストでフォールバックするケースがあり、処理の継続を優先する設計です（ログに警告）。
- DuckDB を用いることでローカルかつ高性能な SQL ベースの処理が可能です。保存処理は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）で設計されています。
- RSS ニュース取得では SSRF 対策、レスポンスサイズ制限、defusedxml による安全な XML パースなどを組み込んでいます。

ディレクトリ構成（抜粋）
-----------------------

src/kabusys/
- __init__.py
- config.py                    -- 環境変数 / 設定管理
- ai/
  - __init__.py                 -- score_news エクスポート
  - news_nlp.py                 -- ニュース NLP スコアリング（score_news）
  - regime_detector.py          -- 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py           -- J-Quants API クライアント（fetch/save）
  - pipeline.py                 -- ETL パイプライン（run_daily_etl 等）
  - etl.py                      -- ETL インターフェース再エクスポート
  - news_collector.py           -- RSS ニュース収集
  - calendar_management.py      -- 市場カレンダー管理 / 営業日ユーティリティ
  - quality.py                  -- 品質チェック（check_missing_data 等）
  - stats.py                    -- 統計ユーティリティ（zscore_normalize）
  - audit.py                    -- 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py          -- ファクター計算（momentum/value/volatility）
  - feature_exploration.py      -- 将来リターン・IC・統計サマリー
- monitoring/                    -- 監視関連（コードベースに依存する箇所）
- strategy/                      -- 戦略レイヤ（コードベース参照）
- execution/                     -- 発注/約定関連（コードベース参照）

上記はこのリポジトリに含まれる主要モジュールの一覧（抜粋）です。

トラブルシューティング
---------------------
- .env が読み込まれない
  - プロジェクトルートの判定はパッケージファイル位置から .git または pyproject.toml を探索します。CI 等で異なる構成の場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、明示的に os.environ を設定してください。
- OpenAI/API の認証エラー
  - OPENAI_API_KEY や JQUANTS_REFRESH_TOKEN が未設定だと ValueError が発生します。ログを確認し .env に設定してください。
- DuckDB ファイルのパス
  - settings.duckdb_path を変えたい場合は .env に DUCKDB_PATH を設定します。デフォルトは data/kabusys.duckdb。

開発・拡張メモ
----------------
- テスト時に外部 API 呼び出しをモックするため、モジュール内の _call_openai_api や _urlopen 等を unittest.mock.patch で差し替えできるよう設計されています。
- 新しい ETL ジョブや品質チェックを追加する場合は data.pipeline.run_daily_etl のフローに沿って個別の run_* 関数を追加してください。
- 監査ログの初期化は init_audit_schema/ init_audit_db を利用。既存テーブルに影響を出さないよう冪等 DDL を用いています。

最後に
------
この README はコードベース内の docstring と設計コメントから作成しています。実運用にあたっては環境変数や API 制限、DB バックアップ方針、ログ収集・監視の運用手順を整備してください。質問や追加のドキュメント化（例: API 使用例、CI/CD の設定など）が必要であれば教えてください。