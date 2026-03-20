KabuSys
=======

日本株向けの自動売買 / データ基盤ライブラリです。  
DuckDB を中核に、J-Quants からのデータ取得、ETL、特徴量生成、シグナル生成、ニュース収集、監査ログなどを含む設計になっています。本リポジトリはライブラリとして各処理をモジュール化しており、バッチ実行や研究用途（research）にも使える構成です。

主な目的
- J-Quants API からの株価・財務・カレンダー取得と DuckDB への冪等保存
- 市場データの品質チェック・前処理
- 戦略用特徴量の計算・正規化（Z スコア）
- ファンドメンタル / モメンタム / ボラティリティに基づくスコアリングと売買シグナル生成
- RSS ベースのニュース収集と銘柄紐付け
- 発注・約定・ポジション管理・監査ログ（スキーマ設計まで）

機能一覧
- data/
  - jquants_client: J-Quants API クライアント（認証、ページネーション、リトライ、レート制御、DuckDB への保存ユーティリティ）
  - pipeline: 日次 ETL（prices / financials / calendar）の差分実行、品質チェック統合
  - schema: DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - news_collector: RSS 収集、前処理、raw_news への冪等保存、銘柄抽出と紐付け
  - calendar_management: JPX カレンダー管理、営業日判定ユーティリティ
  - stats: 汎用統計ユーティリティ（zscore_normalize など）
  - features: zscore_normalize の公開再エクスポート
  - audit: 監査ログ用スキーマ（signal_events / order_requests / executions 等）
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算（prices_daily/raw_financials を参照）
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、要約統計
- strategy/
  - feature_engineering: research で計算した生ファクターを正規化・合成して features テーブルに保存
  - signal_generator: features と ai_scores を統合して final_score を計算し signals テーブルへ保存
- execution/: 発注・ステータス管理（実装の入口）
- config.py: 環境変数設定管理（.env の自動ロード、必須変数チェック）
- monitoring: （パッケージ公開インターフェースに含まれる想定モジュール）

セットアップ手順（開発用）
- 前提
  - Python 3.9+（typing 機能を使用しているため比較的新しいバージョンを推奨）
  - DuckDB を使用（pip でインストール可能）
  - ネットワーク経由で J-Quants / RSS にアクセス可能な環境

例: 仮想環境作成と依存パッケージ（最低限）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （必要に応じて）pip install requests 等（本コードは urllib を使っていますが、環境によって追加ライブラリが必要な場合があります）
   - パッケージ化されている場合は pip install -e . で開発インストール

3. 環境変数 / .env
   - プロジェクトルートに .env（または .env.local）を置くことで自動読み込みされます（config.py が .git または pyproject.toml を基準に探索）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須の環境変数（config.Settings 参照）
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- （任意）DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- （任意）SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）

簡易 .env.example
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- DUCKDB_PATH=data/kabusys.duckdb
- SQLLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

使い方（代表的なワークフロー例）
- DuckDB スキーマ初期化
  - Python REPL / スクリプト例:
    from kabusys.config import settings
    from kabusys.data.schema import init_schema
    conn = init_schema(settings.duckdb_path)  # data/kabusys.duckdb を作成・初期化して接続を返す

- 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- 特徴量の構築（features テーブルへ保存）
    from datetime import date
    from kabusys.strategy import build_features
    build_count = build_features(conn, target_date=date(2024,1,1))
    print(f"built features: {build_count}")

- シグナル生成（signals テーブルへ保存）
    from kabusys.strategy import generate_signals
    total_signals = generate_signals(conn, target_date=date(2024,1,1))
    print(f"signals generated: {total_signals}")

- ニュース収集
    from kabusys.data.news_collector import run_news_collection
    # known_codes: 銘柄抽出に使用する有効なコード集合（例: prices データから取得したコード群）
    res = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
    print(res)

- J-Quants の生データ取得/保存（低レベル API）
    from kabusys.data import jquants_client as jq
    records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
    saved = jq.save_daily_quotes(conn, records)
    print(f"fetched={len(records)} saved={saved}")

注意点・設計方針（要点）
- 自動環境読み込みは config.py により .env / .env.local を探索してロードします。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- DuckDB への保存は基本的に冪等（ON CONFLICT）で実装されています。ETL は差分方式で可能な限り API リクエストを絞る設計です。
- J-Quants クライアントはレート制限・リトライ・トークン自動リフレッシュを内蔵しています（MAX_RETRIES、固定間隔スロットリングなど）。
- strategy 層はルックアヘッドバイアス回避のため target_date 時点のデータのみを参照します（過去データのみ使用）。
- news_collector は SSRF/XML Bomb 対策（スキームの検証、defusedxml、サイズ上限、プライベートホスト拒否など）を実装しています。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - schema.py
    - news_collector.py
    - calendar_management.py
    - audit.py
    - stats.py
    - features.py
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
  - (monitoring モジュール等は公開 API に含まれています)

開発・テスト
- 各モジュールは外部依存を最小にする設計（標準ライブラリ中心、duckdb と defusedxml を使用）です。ユニットテストでは DuckDB の ":memory:" 接続を使うと容易に検証できます。
  - 例: conn = init_schema(":memory:")

ロギング
- settings.log_level でログレベルを制御します。環境変数 LOG_LEVEL を設定してください。

追加情報
- 戦略モデルや DataPlatform の詳細（StrategyModel.md / DataPlatform.md / DataSchema.md 等）はリポジトリのドキュメントに従ってください（本 README はコードコメントやモジュール docstring を要約したものです）。
- 実運用（ライブ発注）を行う場合は、発注レイヤー・証券会社 API の実装、リスク管理、監査ログ運用などを慎重に組み合わせてください。

問題・貢献
- バグや要望があれば Issue を立ててください。プルリク歓迎です。設計に関する改善提案やテストの追加も歓迎します。

以上。必要であれば README に含めるサンプルスクリプト（実行スクリプトや systemd / cron 用の例）、より詳細な .env.example、または各モジュールごとの API リファレンスを別途作成します。必要なものを教えてください。