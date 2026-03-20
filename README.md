# KabuSys

日本株向け自動売買基盤（ライブラリ）です。  
データ収集（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、DBスキーマ／監査などを含むモジュール群を提供します。

バージョン: 0.1.0 (src/kabusys/__init__.py)

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（サンプル）
- 環境変数
- ディレクトリ構成
- 貢献・テストについて

---

プロジェクト概要
- KabuSys は日本株自動売買のための基盤ライブラリです。  
  J-Quants API からのデータ取得、DuckDB を用いたデータ保存／スキーマ、特徴量計算（research）, 戦略のシグナル生成、ニュース収集（RSS）や監査ログのためのスキーマなどを含みます。
- ルックアヘッドバイアス防止、冪等性（DB保存は ON CONFLICT などで制御）、API レート制御、リトライ、SSRF 対策など運用／安全性に配慮した実装方針です。

機能一覧
- 環境設定管理
  - .env / .env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - 必須設定の取得 API（kabusys.config.settings）
- データ取得／保存（kabusys.data.jquants_client）
  - J-Quants からの日次株価、財務データ、マーケットカレンダー取得（ページネーション対応）
  - 取得結果を DuckDB に冪等保存するユーティリティ（save_*）
  - レート制御・リトライ・自動トークンリフレッシュ対応
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl / 個別の ETL ジョブ（価格 / 財務 / カレンダー）
  - 差分取得・バックフィル・品質チェックの仕組み
- スキーマ管理（kabusys.data.schema）
  - DuckDB 用の詳細な DDL と初期化関数 init_schema()
  - Raw / Processed / Feature / Execution 層を定義
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理、記事ID生成（正規化URL→SHA256）、raw_news 保存、銘柄紐付け
  - SSRF 対策・受信サイズ制限・XML セキュリティ対策あり（defusedxml）
- 研究／特徴量計算（kabusys.research.*）
  - momentum / volatility / value 等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン、IC（Spearman）計算、統計サマリー
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - 生ファクターの正規化（Zスコア）・ユニバースフィルタ・features テーブルへの UPSERT
- シグナル生成（kabusys.strategy.signal_generator）
  - features + ai_scores を組み合わせ最終スコアを計算、BUY/SELL シグナルを signals テーブルへ保存
  - Bear レジーム判定、STOP LOSS、エグジット判定など
- 統計ユーティリティ（kabusys.data.stats）
  - zscore_normalize 等（外部依存なし）
- 監査テーブル（kabusys.data.audit）
  - シグナル→発注→約定のトレーサビリティ用テーブル DDL

セットアップ手順（開発環境向けの最小手順）
1. 推奨 Python バージョン
   - Python 3.10 以上（パイプラインで PEP 604 型注釈（X | Y）等を使用）

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール（最小）
   - pip install duckdb defusedxml

   （本リポジトリをパッケージとしてインストールする場合）
   - pip install -e .

   追加で運用や通知等を行う場合は別途ライブラリが必要になることがあります（Slack クライアント等）。

4. 環境変数の用意
   - プロジェクトルートに .env / .env.local を置くと自動的に読み込まれます（kabusys.config が自動ロード）。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで次を実行:

     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - デフォルトの DB パスは settings.duckdb_path（環境変数 DUCKDB_PATH で変更可）。

使い方（基本的な例）
- DB の初期化、日次 ETL 実行（最低限の流れ）

  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  # DB 初期化（ファイルがなければ作成）
  conn = init_schema("data/kabusys.duckdb")

  # 日次 ETL（今日分を取得・保存）
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 特徴量構築 + シグナル生成

  from datetime import date
  from kabusys.strategy import build_features, generate_signals
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  target = date(2024, 1, 10)

  # features を構築（features テーブルへ UPSERT）
  n_features = build_features(conn, target)

  # シグナルを生成（signals テーブルへ UPSERT）
  n_signals = generate_signals(conn, target)
  print("features:", n_features, "signals:", n_signals)

- ニュース収集ジョブ実行（RSS の収集と銘柄紐付け）

  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 実運用では全銘柄集合を用意する
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)

環境変数（主要）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（kabusys.data.jquants_client で利用）
  - KABU_API_PASSWORD: kabuステーション API のパスワード（execution 層で利用）
  - SLACK_BOT_TOKEN: Slack 通知用トークン
  - SLACK_CHANNEL_ID: Slack 通知用チャンネル ID

- 任意 / デフォルトあり
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - KABUSYS_ENV: 実行環境 ("development" / "paper_trading" / "live")（デフォルト: development）
  - LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）

- 自動 .env ロード
  - プロジェクトルート（.git または pyproject.toml がある位置）から .env と .env.local を自動読み込みします。
  - 読み込み優先度: OS 環境 > .env.local > .env
  - テスト時などに自動ロードを無効化したい場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py（__version__ = "0.1.0"）
  - config.py（環境変数・設定管理）
  - data/
    - __init__.py
    - jquants_client.py（J-Quants API クライアント、取得／保存機能）
    - news_collector.py（RSS 収集・記事保存・銘柄抽出）
    - schema.py（DuckDB スキーマ／init_schema）
    - pipeline.py（ETL パイプライン）
    - features.py（zscore_normalize の再エクスポート）
    - stats.py（統計ユーティリティ）
    - calendar_management.py（マーケットカレンダー管理）
    - audit.py（監査／トレーサビリティ DDL）
    - quality.py（品質チェックは pipeline から参照：注：quality モジュールの実装は別ファイルが想定されます）
  - research/
    - __init__.py（research API のエクスポート）
    - factor_research.py（momentum/value/volatility 等）
    - feature_exploration.py（forward returns, IC, summary）
  - strategy/
    - __init__.py（build_features, generate_signals をエクスポート）
    - feature_engineering.py（features 作成）
    - signal_generator.py（シグナル生成）
  - execution/ （発注・約定関連の実装を置く場所）
  - monitoring/ （監視用コンポーネント）

補足・注意点
- DuckDB の型や制約を活用したスキーマ設計になっています。init_schema() は冪等で何度でも実行できます。
- J-Quants の API レート制限（120 req/min）に基づく簡単なレートリミッタとリトライ戦略を実装しています。
- ニュース収集は外部 RSS をダウンロードするため、ネットワーク／セキュリティ周りの設定に注意してください（SSRF 対策、受信サイズ上限などを実装済み）。
- strategy 層は features / ai_scores / positions 等の DB テーブルを参照します。運用時は positions や ai_scores の更新ロジック（モデル等）を組み合わせてください。

貢献・テスト
- バグ修正・機能追加は PR を歓迎します。ユニットテストと linters を用意することを推奨します。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境依存を切り離してください。
- DuckDB のインメモリ DB（":memory:"）を用いるとテストが高速になります:
  conn = init_schema(":memory:")

---

README は以上です。必要ならば、インストール時の requirements.txt、サンプルスクリプト、.env.example のテンプレート、或いは各モジュールの詳細設計（StrategyModel.md / DataPlatform.md 等）に基づく運用ガイドを別途作成します。どの章を詳細化しますか？