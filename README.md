KabuSys — 日本株自動売買基盤（README）
=================================

概要
----
KabuSys は日本株のデータ取得・品質チェック・研究（ファクター/特徴量解析）・AI を用いたニュースセンチメント評価・市場レジーム判定・監査ログ管理などを包含するシンプルな自動売買基盤のライブラリ群です。DuckDB をデータレイヤに採用し、J-Quants API からマーケットデータを取得、OpenAI を用いたニュースセンチメント評価を行う設計になっています。

主な目的
- データ ETL（株価・財務・カレンダー等）の自動化と品質チェック
- ニュース記事の収集・NLP による銘柄別センチメント算出
- マーケットレジーム判定（ETF + マクロニュースの組合せ）
- 研究用ファクター計算・特徴量解析ユーティリティ
- 監査ログ（シグナル→発注→約定トレース）用スキーマ初期化

機能一覧
--------
- 環境変数/設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動ロード（無効化可）
  - 必須変数チェック / env 切替（development/paper_trading/live）
- データ取得・ETL（kabusys.data）
  - J-Quants API クライアント（レートリミット・リトライ・トークン自動更新）
  - 日次 ETL パイプライン（run_daily_etl）
  - 市場カレンダー管理（営業日判定・バッチ更新）
  - ニュース収集（RSS の安全な取得・前処理）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（監査テーブル定義・初期化ユーティリティ）
  - 汎用統計ユーティリティ（Zスコア正規化等）
- 研究（kabusys.research）
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI（kabusys.ai）
  - ニュース NLP（銘柄別センチメント算出: score_news）
  - レジーム判定（ETF MA + マクロニュース：score_regime）
  - OpenAI API 呼び出しは堅牢なリトライ/フォールバック設計
- 監視・実行（パッケージ基盤、PID・リソース閾値などの設定を提供）

セットアップ手順
---------------
1. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - 必要な主なライブラリ:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）

3. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）から以下ファイルを自動で読み込みます:
     - .env （優先度: OS 環境変数 > .env.local > .env）
     - .env.local（.env 上書き）
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API 用パスワード
   - SLACK_BOT_TOKEN: Slack 通知用トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネルID
   - OPENAI_API_KEY: OpenAI 呼び出し時に必要（関数引数で上書き可）
   - その他（任意・デフォルト有り）:
     - KABUSYS_ENV (development|paper_trading|live) — デフォルト development
     - LOG_LEVEL (DEBUG|INFO|...)
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用デフォルト data/monitoring.db）
     - PID_FILE_PATH、CPU_THRESHOLD_PCT、MEMORY_THRESHOLD_PCT 等

5. データベースの初期化（監査 DB の例）
   - Python で:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")

使い方（簡単な例）
-----------------

- DuckDB 接続の作成（ライブラリ全般で使用）
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))  # settings は kabusys.config.settings

- 日次 ETL の実行
  - from kabusys.data.pipeline import run_daily_etl
  - from kabusys.config import settings
  - import duckdb, datetime
  - conn = duckdb.connect(str(settings.duckdb_path))
  - result = run_daily_etl(conn, target_date=datetime.date(2026, 3, 20))
  - print(result.to_dict())

- ニュースのセンチメントスコア算出（AI）
  - from kabusys.ai.news_nlp import score_news
  - score_count = score_news(conn, target_date=datetime.date(2026,3,20), api_key="sk-...")
  - 戻り値は書き込み済み銘柄数（ai_scores に書き込み）

- マーケットレジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=datetime.date(2026,3,20), api_key="sk-...")

- ファクター計算 / 研究関数
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - mom = calc_momentum(conn, target_date=datetime.date(2026,3,20))

- 監査テーブル初期化
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn, transactional=True)

- 環境変数取得例
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env などを参照

挙動のポイント / 注意点
-----------------------
- .env 読み込み
  - プロジェクトルートを __file__ の親から探索（CWD に依存しない）。
  - OS の環境変数はデフォルトで保護され .env の値で上書きされない（.env.local は上書き可）。
- Look-ahead bias の回避
  - モジュールの多くは date 引数を受け取る; datetime.today() を直接参照しない設計です。バックテスト時は対象日の指定に注意してください。
- OpenAI / J-Quants 呼び出し
  - リトライ、指数バックオフ、API エラーのフォールバックが実装されています。API キー未設定時は関数が ValueError を投げます。
- DuckDB executemany の空リスト制約や一部の SQL 挙動（バージョン差）に注意した実装があります。
- ニュース収集は SSRF 対策・応答サイズ制限・XML を安全に扱うための実装が含まれています。

ディレクトリ構成（主なファイル/モジュール）
--------------------------------------
- src/kabusys/
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
    - pipeline.py (ETLResult export)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/（export helpers）
  - その他（strategy / execution / monitoring 等の名前空間は __all__ に準備）

ドキュメント / 設計ノート
-----------------------
- 各モジュールの docstring に設計方針や処理フロー、フェイルセーフの挙動が記載されています。実運用に移す前に下記点を確認してください:
  - J-Quants のレート制限・API 利用規約
  - OpenAI の利用ポリシー・トークン管理
  - DuckDB ファイルのバックアップと排他アクセス（複数プロセスでの同時書込みは注意）
  - 監査ログ（audit）テーブルは削除しない前提の設計

サンプル .env（例）
------------------
以下は必要な最小の環境変数例（実際の値は秘匿して下さい）:

- JQUANTS_REFRESH_TOKEN=...
- OPENAI_API_KEY=...
- KABU_API_PASSWORD=...
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- KABUSYS_ENV=development
- DUCKDB_PATH=data/kabusys.duckdb

サポート / 開発
----------------
- 開発時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効化できます（テストなど）。
- 単体テストやモック可能な設計（OpenAI 呼び出しや HTTP 層の差替えが可能）になっています。テスト実行時は該当関数を patch して外部 API 依存を切り離してください。

ライセンス
---------
- この README では記載しません。実プロジェクトでは LICENSE を別途配置してください。

補足
----
- 上記はソース内コメント／docstring に基づく概要と利用方法のまとめです。より詳細な API の利用法や各関数の引数/返り値については該当モジュールの docstring を参照してください。