KabuSys — 日本株自動売買プラットフォーム
=================================

概要
----
KabuSys は日本株のデータプラットフォームとリサーチ／戦略実装のための内部ライブラリ群です。  
主に以下を提供します。

- J-Quants API 経由の ETL（株価 / 財務 / 市場カレンダー）の差分取得・保存（DuckDB）
- ニュース収集（RSS）と LLM によるニュースセンチメント評価（OpenAI）
- 市場レジーム判定（ETF の MA とマクロニュース合成）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）と特徴量解析ユーティリティ
- データ品質チェック、マーケットカレンダー管理、監査ログ（発注→約定のトレーサビリティ）

設計上のポイント
- ルックアヘッドバイアス防止（内部で date.today()/datetime.today() を不用意に参照しない設計）
- DuckDB を中心としたローカルデータベース設計（ETL は冪等性を重視）
- OpenAI 呼び出しはリトライやフォールバック実装あり（API障害時は安全側にフォールバック）
- セキュリティ配慮（ニュース収集の SSRF 対策、XML パースの安全化 等）

主な機能一覧
----------------
- data
  - ETL（pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系関数）
  - カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
  - ニュース収集（RSS fetch_rss、前処理、raw_news 保存ロジック）
  - 品質チェック（missing_data / duplicates / spike / date_consistency / run_all_checks）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news：銘柄単位の sentiment を ai_scores に書き込む）
  - 市場レジーム判定（score_regime：ETF MA とマクロニュースを合成して market_regime に書込）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量解析（calc_forward_returns / calc_ic / factor_summary / rank）

必要要件（想定）
- Python 3.10+
- pip でインストールする主な依存パッケージ（プロジェクトに requirements.txt がある場合はそちらを参照してください）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース）

セットアップ手順
----------------
1. リポジトリをクローン（もしくはパッケージを取得）
   - git clone ...

2. 開発環境にパッケージをインストール
   - 任意の仮想環境を作成してアクティベート後:
     - pip install -e . 
     - または requirements.txt がある場合: pip install -r requirements.txt

3. 環境変数の設定
   - ルートディレクトリに .env ファイルを作成します（.env.example を参考にしてください）。
   - 主な必須変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
     - KABU_API_PASSWORD — kabuステーション API のパスワード（発注機能を使う場合）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — 通知用（Slack）
     - OPENAI_API_KEY — OpenAI 呼び出しに使用（ai.score_news / ai.score_regime）
   - オプション:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — パッケージインポート時の .env 自動読み込みを無効化
     - KABUSYS_ENV — development / paper_trading / live
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL

   例 (.env):
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     SLACK_BOT_TOKEN=xoxb-xxxx
     SLACK_CHANNEL_ID=C0123456
     KABU_API_PASSWORD=yourpassword
     DUCKDB_PATH=data/kabusys.duckdb

   補足:
   - パッケージは import 時にプロジェクトルート（.git または pyproject.toml を起点）を探索し、.env / .env.local を自動読み込みします。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. データベース初期化（監査DB など）
   - 監査用 DuckDB を初期化する例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
   - 一般的なデータ格納先は settings.duckdb_path（デフォルト data/kabusys.duckdb）

使い方（簡単なコード例）
-----------------------
- 日次 ETL を実行してデータを取得・保存する（例: target_date に対する処理）

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースのセンチメントを生成する（ai.score_news）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # OPENAI_API_KEY を .env に設定しておく
  print("書き込んだ銘柄数:", n_written)

- 市場レジームをスコアリングして保存する（ai.regime_detector.score_regime）

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20), api_key=None)  # api_key None -> 環境変数 OPENAI_API_KEY を使用

- ファクター計算・特徴量探索（research）

  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum
  from kabusys.data.stats import zscore_normalize

  conn = duckdb.connect(str(settings.duckdb_path))
  records = calc_momentum(conn, date(2026,3,20))
  normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])

注意点 / 実運用のポイント
- OpenAI 呼び出しはレート制限や API 障害があり得ます。score_news / score_regime はフォールバックやリトライ実装を行い、API 失敗時は安全側（0.0 等）で継続する設計です。
- ETL は冪等性を重視しており、save_ 関数は ON CONFLICT DO UPDATE（重複更新）となっています。
- データ品質チェック（data.quality.run_all_checks）は ETL 後に実行して、品質問題を検出・監査ログに残すことを推奨します。
- 監査ログ（data.audit）は、発注→約定のトレーサビリティを確保するためのテーブルとインデックスを初期化します。init_audit_db により UTC タイムゾーンで初期化されます。
- Look-ahead バイアス対策のため、関数は target_date を明示的に渡す設計が多く、内部で現在時刻を直接参照しないように注意されています。

ディレクトリ構成（概要）
-----------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / 設定ロード
- ai/
  - __init__.py
  - news_nlp.py                   — ニュースセンチメント解析（score_news）
  - regime_detector.py            — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント（fetch/save）
  - pipeline.py                   — ETL パイプラインと run_daily_etl
  - etl.py                        — ETL インターフェース再エクスポート
  - calendar_management.py        — マーケットカレンダー管理
  - news_collector.py             — RSS ニュース収集・前処理
  - quality.py                    — データ品質チェック
  - stats.py                      — 統計ユーティリティ（zscore_normalize）
  - audit.py                      — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py            — ファクター算出（momentum/value/volatility）
  - feature_exploration.py        — 将来リターン / IC / summary
- research/...（その他実験的ユーティリティ）
- その他: strategy / execution / monitoring パッケージが __all__ に想定されています（現状コードベース参照）

付録: 重要な環境変数と意味
--------------------------
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携がある場合）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH / SQLITE_PATH: データベースファイルパス（デフォルト data/kabusys.duckdb, data/monitoring.db）
- KABUSYS_ENV: 環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル

おわりに
--------
この README はコードベースから抽出した機能と想定される使い方をまとめたものです。実行時の詳細な挙動や API レスポンス形式、スキーマ詳細などは各モジュール（特に data/jquants_client.py、data/pipeline.py、ai/news_nlp.py 等）の docstring を参照してください。追加の使い方（例：戦略のシグナル生成・発注フローやモニタリング機能）を実装する場合は、監査ログ（data.audit）や発注の冪等性に注意して拡張してください。