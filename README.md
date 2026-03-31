KabuSys — 日本株自動売買プラットフォーム
======================================

概要
----
KabuSys は日本株向けのデータ基盤・リサーチ・戦略・監査ログを備えた自動売買用ライブラリ群です。  
主に以下を目的とします。

- J-Quants API からの株価・財務・マーケットカレンダー等の ETL パイプライン
- ニュースの収集と LLM を用いたニュースセンチメント（ai_score）生成
- 市場レジーム判定（ETF + マクロニュースを合成）
- 研究用ファクター計算・特徴量探索（Momentum / Value / Volatility 等）
- 監査ログ（signal → order_request → execution）の永続化（DuckDB）
- データ品質チェック・カレンダー管理・監視ユーティリティ

この README はリポジトリ内のソース構造（src/kabusys 以下）に基づき、セットアップと基本的な使い方をまとめたものです。

主な機能
--------
- ETL（data.pipeline）
  - 差分取得 / バックフィル / 保存（冪等） / 品質チェックを組み合わせた日次 ETL
- J-Quants クライアント（data.jquants_client）
  - 株価（daily_quotes）、財務（statements）、マーケットカレンダー取得／保存（DuckDB）
  - レート制御・リトライ・トークン自動リフレッシュを実装
- ニュース収集（data.news_collector）
  - RSS からの記事収集、前処理、SSRF 対策、冪等保存
- ニュース NLP（ai.news_nlp）
  - OpenAI（gpt-4o-mini）を使った銘柄ごとのセンチメント算出と ai_scores への保存
- 市場レジーム判定（ai.regime_detector）
  - ETF 1321 の MA200 乖離とマクロニュースの LLM スコアを合成して日次レジーム判定
- 研究モジュール（research/*）
  - ファクター計算（momentum/value/volatility）、将来リターン・IC・統計サマリ等
- データ品質チェック（data.quality）
  - 欠損・スパイク・重複・日付不整合検出
- 監査ログ（data.audit）
  - signal_events / order_requests / executions 等のテーブル定義と初期化ユーティリティ

前提・依存
----------
- Python 3.10+（typing の | 記法を使用）
- 必要パッケージ（代表）:
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ（urllib, json, datetime, logging 等）

セットアップ手順
---------------
1. リポジトリをクローンして develop 環境に入る（例: pip editable）
   - 推奨: 仮想環境を作成してからインストールしてください。
     python -m venv .venv
     source .venv/bin/activate

2. 必要パッケージをインストール
   - 最低限:
     pip install duckdb openai defusedxml
   - 開発用に requirements ファイルや poetry がある場合はそちらを利用してください（本リポジトリの実装に合わせて）。

3. 環境変数の設定
   - プロジェクトルートに .env ファイルを置くと自動的に読み込まれます（モジュール起動時に .git または pyproject.toml をルートとして探索）。
   - 自動読み込みを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   - 必須の主な環境変数（config.Settings を参照）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news/score_regime 用）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（発注機能を使う場合）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知（必要に応じて）
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: 監視用 sqlite（data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

   - サンプル .env（例）
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
     OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

4. データベース初期化（監査ログなど）
   - 監査 DB を初期化する例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
   - または既存の DuckDB 接続にスキーマを追加:
     from kabusys.data.audit import init_audit_schema
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn, transactional=True)

使い方（簡単なコード例）
---------------------

- DuckDB 接続と ETL の実行
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアリング（AI）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY を環境変数に設定していれば api_key 引数は不要
  n_written = score_news(conn, target_date=date(2026,3,20))
  print("wrote", n_written, "ai_scores")

- 市場レジーム判定
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20))

- ファクター計算 / 研究
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize

  conn = duckdb.connect(str(settings.duckdb_path))
  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  mom_z = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

運用上の注意
-------------
- Look-ahead バイアス回避
  - 多くのモジュールは datetime.today() や date.today() を直接参照せず、target_date を明示的に渡す設計です（バックテストや再現性のため）。
- OpenAI 呼び出し
  - API レスポンスのパース失敗や呼び出し失敗時はフェイルセーフとして 0.0（中立）にフォールバックする実装があるため、API 機能の部分的な障害で全体が即座に停止することは減ります。
  - テストのために内部の _call_openai_api をモックできます（例: unittest.mock.patch）。
- 環境変数の自動読み込み
  - パッケージ import 時点でプロジェクトルート（.git または pyproject.toml）から .env / .env.local を読み込みます。テスト等でこれを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数と設定の取得（Settings）
- ai/
  - __init__.py
  - news_nlp.py            — ニュースセンチメント（score_news）
  - regime_detector.py     — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - pipeline.py            — ETL（run_daily_etl 等）・ETLResult
  - jquants_client.py      — J-Quants API クライアント（fetch / save）
  - news_collector.py      — RSS 収集および前処理
  - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
  - quality.py             — データ品質チェック
  - audit.py               — 監査ログスキーマ定義・初期化
  - etl.py                 — ETLResult の公開再エクスポート
  - stats.py               — 汎用統計ユーティリティ（zscore_normalize）
- research/
  - __init__.py
  - factor_research.py     — Momentum/Value/Volatility 等
  - feature_exploration.py — 将来リターン/IC/factor_summary 等

テスト・デバッグ
----------------
- OpenAI 呼び出しや外部 API 呼び出しはモックしてユニットテストを実行してください。
- news_collector.py には SSRF 対策や応答サイズ検査が組み込まれています。ネットワーク関連のテストでは外部接続をスタブ化することを推奨します。
- settings からの自動 .env ロードはテスト時に副作用を招く可能性があるため、KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化できます。

ライセンス・贡献
----------------
- この README ではライセンス・貢献手順は記載されていません。実際のリポジトリでは LICENSE / CONTRIBUTING 等のファイルを参照してください。

補足（実装に関する要点）
-----------------------
- DuckDB をデータストアとして利用し、ETL は冪等に設計されています（ON CONFLICT 等）。
- J-Quants API はレート制御・トークン自動更新・ページネーションに対応。
- OpenAI 呼び出しは JSON Mode を前提とし、レスポンスの冗長テキスト混入に備えた復元処理やリトライを実装。
- ニュース収集は URL 正規化（utm 等の除去）、記事 ID は URL の SHA-256 ハッシュで冪等化されています。

――――――――――――――――――――――――
必要な情報やより具体的なユースケース（例: 発注実行フロー、Slack 通知連携、運用スケジュール設定など）について追記が必要であれば教えてください。README にサンプル .env.example や具体的な CLI ランナー例を追加できます。