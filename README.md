# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計された Python ライブラリ群です。
J-Quants からの市場データ取得・DuckDB への永続化、研究用ファクター計算、特徴量生成、シグナル作成、
RSS ニュース収集、マーケットカレンダー管理、発注・監査ログのスキーマなどを含むデータパイプラインと戦略レイヤーを提供します。

## 主要な特徴（概要）
- J-Quants API クライアント（レート制御・リトライ・トークン自動更新を備えた取得/保存機能）
- DuckDB ベースのスキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリューなど）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ・日付単位の冪等アップサート）
- シグナル生成（ファクター + AI スコア統合、BUY/SELL 判定、エグジット判定）
- RSS ニュース収集と銘柄紐付け（SSRF 対策・トラッキング除去・重複排除）
- マーケットカレンダー管理（JPX カレンダー取得・営業日判定ユーティリティ）
- 監査ログ（signal → order → execution のトレース用スキーマ）

## 機能一覧（モジュール別）
- kabusys.config
  - .env / 環境変数の自動ロード（.env, .env.local）・必須設定取得
- kabusys.data
  - jquants_client: API 取得・永続化（raw_prices / raw_financials / market_calendar 等）
  - schema: DuckDB スキーマの作成 / 初期化
  - pipeline: 日次 ETL ジョブ（run_daily_etl など）
  - news_collector: RSS 収集・前処理・DB 保存・銘柄抽出
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - stats: z-score 正規化ユーティリティ
  - features: zscore_normalize の公開ラッパ
  - audit: 監査ログ用 DDL（signal_events / order_requests / executions 等）
- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: 将来リターン計算, IC, 統計サマリ等
- kabusys.strategy
  - feature_engineering.build_features: features テーブル作成（Z スコア正規化 + クリップ）
  - signal_generator.generate_signals: features + ai_scores を統合して signals を生成
- その他
  - news_collector の SSRF 対策、gzip サイズ制限、記事 ID の冪等性等の堅牢化実装

## 必要な環境
- Python 3.9+（typing の一部構文から 3.10+ を想定する箇所もありますが、3.9 以降で動作するように記述されています）
- 主な依存パッケージ（プロジェクトの requirements.txt がある場合はそちらを使用してください）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API、RSS フィード等）

※ 実行環境や CI での細かい依存はプロジェクトの packaging / requirements を参照してください。

## 環境変数（主要）
以下は本システムで利用される主要な環境変数です（必須は README に明記）。

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants の refresh token
- KABU_API_PASSWORD : kabu ステーション API パスワード
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : 実行環境 (development | paper_trading | live)。デフォルト: development
- LOG_LEVEL : ログレベル（DEBUG, INFO, ...）。デフォルト: INFO

自動読み込みの制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化できます（テスト用途など）。

.env ファイルの扱い:
- プロジェクトルート（.git または pyproject.toml を探して）を基準に .env と .env.local を順に読み込みます。
  - OS 環境 > .env.local > .env の優先順位で値が決定されます。
  - .env.local は .env の上書き用に使ってください。

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （もしパッケージとしてインストールする場合）pip install -e .

   ※ packaging に requirements.txt / pyproject.toml があればそちらを使ってください。

3. 環境変数を設定
   - プロジェクトルートに .env（および必要なら .env.local）を作成して必須変数を設定してください。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=secret
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb

4. DuckDB スキーマ初期化
   Python REPL またはスクリプトで:
   >>> from kabusys.data.schema import init_schema
   >>> conn = init_schema("data/kabusys.duckdb")
   これにより必要なテーブルとインデックスが作成されます。

## 使い方（主要な操作例）
以下は代表的なワークフロー例です。

1) 日次 ETL（市場カレンダー・株価・財務の差分取得）
- Python から:
  >>> from datetime import date
  >>> import kabusys
  >>> from kabusys.data.schema import init_schema, get_connection
  >>> from kabusys.data.pipeline import run_daily_etl
  >>>
  >>> conn = init_schema("data/kabusys.duckdb")
  >>> result = run_daily_etl(conn, target_date=date.today())
  >>> print(result.to_dict())

2) 特徴量の構築（research の raw factor を正規化して features テーブルへ保存）
  >>> from datetime import date
  >>> from kabusys.data.schema import get_connection
  >>> from kabusys.strategy import build_features
  >>> conn = get_connection("data/kabusys.duckdb")
  >>> n = build_features(conn, target_date=date(2024, 1, 31))
  >>> print(f"upserted {n} features")

3) シグナル生成（features + ai_scores を集計して signals を生成）
  >>> from datetime import date
  >>> from kabusys.strategy import generate_signals
  >>> conn = get_connection("data/kabusys.duckdb")
  >>> total = generate_signals(conn, target_date=date(2024,1,31))
  >>> print(f"generated {total} signals")

4) RSS ニュース収集ジョブの実行
  >>> from kabusys.data.news_collector import run_news_collection
  >>> conn = get_connection("data/kabusys.duckdb")
  >>> known_codes = {"7203", "6758", "9984", ...}  # 既知銘柄セット（必要に応じて）
  >>> results = run_news_collection(conn, sources=None, known_codes=known_codes)
  >>> print(results)

5) カレンダー更新ジョブ（夜間バッチ）
  >>> from kabusys.data.calendar_management import calendar_update_job
  >>> conn = get_connection("data/kabusys.duckdb")
  >>> saved = calendar_update_job(conn)
  >>> print(f"saved {saved} calendar records")

注意:
- 各種関数は DuckDB の接続オブジェクト (duckdb.DuckDBPyConnection) を受け取ります。init_schema は DB の初期化と接続を返します。
- run_daily_etl では品質チェック機能（quality モジュール）を呼び出します。品質チェックで問題が見つかっても ETL は継続し、issue が ETLResult に格納されます。

## 設計・運用上のポイント（重要）
- ルックアヘッドバイアス回避: ファクター計算やシグナル生成は target_date 時点の利用可能データのみを使用するよう設計されています。
- 冪等性: DB 保存処理は ON CONFLICT を用いたアップサート／DO NOTHING を多用し、再実行に耐えるようにしています。
- トークン管理: J-Quants API 呼び出しはトークン自動リフレッシュとリトライを行い、ページネーション中は ID トークンをキャッシュして使いまわします。
- セキュリティ:
  - news_collector は SSRF、XML Bomb、圧縮爆弾対策やトラッキングパラメータ除去を実装しています。
  - 環境変数・シークレットは .env 等で管理し、.env の取り扱いに注意してください。
- 運用モード:
  - KABUSYS_ENV により development / paper_trading / live の動作差を想定（ログ・チェック・実行ポリシーの切替に利用）。

## ディレクトリ構成（概要）
プロジェクトの主要ファイル構成（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
    - stats.py
    - (その他: quality.py など品質チェックモジュールが想定される)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/  (パッケージエクスポートに含まれるが別途実装が想定される)

（上記はこのリポジトリ内に含まれる主なモジュールを抜粋したものです。実際のリポジトリには追加のユーティリティやテスト、ドキュメントがある場合があります。）

## 開発・拡張のヒント
- 新しい研究ファクターは kabusys.research.factor_research に関数を追加し、strategy.feature_engineering で正規化後に features に含めてください。
- AI スコア連携: ai_scores テーブルの作成は schema.py に含まれており、外部の AI 推論バッチが日次で ai_scores を挿入する想定です。
- 発注・約定フローは audit / execution 層のスキーマに基づいて実装できます。order_request_id を冪等キーとして扱うことで二重発注を防ぎます。

## トラブルシュート（よくある質問）
- .env が読み込まれない:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD がセットされていないか確認してください。
  - プロジェクトルートの検出は __file__ の親ディレクトリ上で .git または pyproject.toml を探しています。ローカルでテストする場合は手動で環境変数を export してください。
- DuckDB の接続 / スキーマに関するエラー:
  - init_schema を呼ばずに get_connection だけ使うとスキーマ未初期化のためテーブルが存在しません。初回は init_schema を使ってください。
- J-Quants の認証エラー:
  - JQUANTS_REFRESH_TOKEN が有効か確認し、rate limit を超えていないかログを確認してください。get_id_token は 401 時に自動リフレッシュを試みます。

---

詳細な API ドキュメントや実運用に関するポリシー（リスク管理、ポートフォリオ構築、発注レート制御）は別途ドキュメント（StrategyModel.md, DataPlatform.md, Audit.md など）で管理することを推奨します。README は入門と基本的な操作フローの案内を目的としています。ご了承ください。