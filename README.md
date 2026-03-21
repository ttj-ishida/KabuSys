KabuSys
======

日本株向けの自動売買プラットフォーム用ライブラリ群（データ取得・処理、研究用ファクター、戦略シグナル生成、監査/スキーマ等）です。本リポジトリは DuckDB を用いたデータレイク／特徴量生成／シグナル生成までの主要コンポーネントを提供します。

主な設計方針
- ルックアヘッドバイアスを避ける（各処理は target_date 時点の情報のみを使用）
- DuckDB を単一の永続ストアとして採用（インメモリも可）
- API 呼び出しはレート制限・リトライ等を配慮して実装
- DB への保存は冪等（ON CONFLICT / upsert）設計
- 研究（research）と本番（execution）を分離して実装

機能一覧
- 環境変数・設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（無効化可）と必須設定チェック
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足・財務・市場カレンダー等の取得、リトライ・レート制御・トークン自動リフレッシュ
  - DuckDB への保存用ユーティリティ（save_*）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（バックフィル対応）／保存／品質チェック（quality モジュール呼び出し）
  - 日次 ETL エントリ（run_daily_etl）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・前処理・DB 保存・銘柄抽出（SSRF 対策・サイズ制限・XML 安全パース）
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / get_trading_days 等のユーティリティ
  - 夜間カレンダー更新ジョブ（calendar_update_job）
- 研究・ファクター計算（kabusys.research）
  - momentum / volatility / value 等のファクター計算
  - 将来リターン・IC（情報係数）・統計サマリー等
- 特徴量生成（kabusys.strategy.feature_engineering）
  - research で得た raw factor を正規化・フィルタ・クリップして features テーブルへ UPSERT
- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合し final_score を算出、BUY/SELL シグナルを生成して signals テーブルへ保存
- 監査・トレーサビリティ（kabusys.data.audit）
  - signal → order_request → executions までの監査ログ定義（UUID ベースの連鎖）

前提・依存関係
- Python 3.10+
  - 型注記で X | Y を使用しているため Python 3.10 以上を想定
- 必要パッケージ（主なもの）
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib, logging, gzip, hashlib, ipaddress 等）を多数使用

セットアップ手順（開発向け）
1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを使ってください）
   - 開発インストール（任意）:
     - pip install -e .

3. 環境変数設定
   - .env または実際の環境変数で以下を設定してください（最低限必須なもの）
     - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン（必須）
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）
   - オプション／デフォルト:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/…（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化できます
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
   - 例（.env）:
     - JQUANTS_REFRESH_TOKEN=xxxx
     - KABU_API_PASSWORD=xxxx
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567

初期化（DuckDB スキーマ作成）
- Python REPL またはスクリプト例:
  - from kabusys.config import settings
    from kabusys.data.schema import init_schema
    conn = init_schema(settings.duckdb_path)
  - init_schema(":memory:") でインメモリ DB を使えます

基本的な使い方（代表的な API）
- 日次 ETL を実行してデータを収集・保存する
  - from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_daily_etl
    conn = init_schema("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- 特徴量（features）を作成する
  - from datetime import date
    from kabusys.strategy import build_features
    from kabusys.data.schema import get_connection
    conn = get_connection("data/kabusys.duckdb")
    n = build_features(conn, target_date=date(2026, 1, 20))
    print(f"upserted features: {n}")

- シグナル生成
  - from datetime import date
    from kabusys.strategy import generate_signals
    n = generate_signals(conn, target_date=date(2026, 1, 20))
    print(f"signals written: {n}")

- ニュース収集ジョブ
  - from kabusys.data.news_collector import run_news_collection
    saved_map = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
    print(saved_map)

- カレンダー更新ジョブ
  - from kabusys.data.calendar_management import calendar_update_job
    saved = calendar_update_job(conn)
    print("saved calendar records:", saved)

設定参照（settings）
- kabusys.config.settings 経由で設定にアクセスできます（例: settings.duckdb_path）
- 主なプロパティ:
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url
  - slack_bot_token, slack_channel_id
  - duckdb_path, sqlite_path
  - env, log_level, is_live, is_paper, is_dev

よくあるワークフロー（例）
1. init_schema で DB を初期化
2. run_daily_etl を夜間に回して daily raw/processed を更新
3. research 側でファクター改善・検証を行う
4. build_features で特徴量を作成
5. generate_signals でシグナルを生成
6. execution 層（別モジュールや外部プロセス）で order_request → 発注 → executions を処理し audit テーブルに記録

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py            — J-Quants API クライアント（取得・保存）
      - news_collector.py            — RSS ニュース収集
      - schema.py                    — DuckDB スキーマ定義・初期化
      - stats.py                     — 統計ユーティリティ（zscore_normalize 等）
      - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
      - features.py                  — data.stats の公開インターフェース
      - calendar_management.py       — カレンダー管理（営業日判定・更新ジョブ）
      - audit.py                     — 監査ログ DDL / 初期化補助
    - research/
      - __init__.py
      - factor_research.py           — momentum/value/volatility 等
      - feature_exploration.py       — 将来リターン・IC・summary 等
    - strategy/
      - __init__.py
      - feature_engineering.py       — features テーブル作成処理
      - signal_generator.py          — final_score 計算・signals 書き込み
    - execution/                      — 発注/監視系（空ディレクトリの可能性あり）
    - monitoring/                     — 監視／メトリクス系（空ディレクトリの可能性あり）

開発上の注意
- DB スキーマの互換性: DuckDB のバージョン差異に注意（DDL の一部制約はバージョン依存の挙動がある）
- 環境変数自動読み込み: config モジュールはパッケージファイル位置からプロジェクトルート（.git または pyproject.toml）を探して .env/.env.local を自動読み込みします。テスト時などで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- レート制限とトークン管理: J-Quants はレート制限があるため jquants_client の RateLimiter に従ってください。401 時のトークン再取得や 429/5xx の指数バックオフが組み込まれています。
- ニュース収集の安全性: fetch_rss は SSRF/プライベートIP・XML Bomb・gzip サイズ等の防御処理を備えています。外部ソースの追加時は source URL の妥当性を確認してください。

ライセンス・貢献
- 本リポジトリのライセンス・貢献方法についてはプロジェクトルートの LICENSE / CONTRIBUTING（存在する場合）を参照してください。

お問い合わせ
- 実運用に関する質問や追加機能のリクエストは Issue を立ててください。README に書かれていない内部仕様（StrategyModel.md、DataPlatform.md 等）に関してはリポジトリ内の該当ドキュメントを参照してください。

以上。必要であればセットアップスクリプト例、CI 用の簡単なコマンドやデバッグ手順（ロギング設定やローカルでの API モック方法）も追記します。どの情報を優先的に追加しますか？