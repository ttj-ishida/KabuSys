# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。データ収集・ETL、ファクター作成、シグナル生成、ニュース収集、監査用スキーマ等を含むモジュール群を提供します。

## プロジェクト概要
KabuSys は以下を目的とした Python モジュール群です。
- J-Quants からの市場データ・財務データの差分取得と DuckDB への保存（ETL）
- 株価・財務を元にしたファクター計算（research）
- ファクター正規化 → features テーブルへの保存（strategy.feature_engineering）
- 正規化済みファクターと AI スコアを統合して売買シグナルを生成（strategy.signal_generator）
- RSS ベースのニュース収集・前処理・銘柄紐付け（data.news_collector）
- DuckDB スキーマ定義・初期化・監査ログ（data.schema / data.audit）
- market calendar 管理、カレンダーを使った営業日判定（data.calendar_management）

設計は「ルックアヘッドバイアス回避」「冪等性（idempotency）」「API レート制御」「トレーサビリティ」を重視しています。

## 主な機能一覧
- J-Quants API クライアント（jquants_client）
  - レートリミット管理・リトライ・トークン自動リフレッシュ
  - 株価・財務・マーケットカレンダーの取得 + DuckDB への冪等保存
- ETL パイプライン（data.pipeline）
  - 差分取得（バックフィル対応）・品質チェック・一括実行（run_daily_etl）
- DuckDB スキーマ初期化（data.schema.init_schema）
- ファクター計算（research.factor_research）
  - Momentum / Volatility / Value 等
- 特徴量エンジニアリング（strategy.feature_engineering.build_features）
  - ユニバースフィルタ、Zスコア正規化、features テーブルへの日付単位置換
- シグナル生成（strategy.signal_generator.generate_signals）
  - 複数コンポーネントスコア、重み付け、Bear レジーム抑制、BUY/SELL 判定、signals テーブルへの保存
- ニュース収集（data.news_collector）
  - RSS 取得、前処理、記事ID生成（URL 正規化 + SHA-256）、raw_news 保存、銘柄抽出と紐付け
- カレンダー管理・営業日ユーティリティ（data.calendar_management）
- 統計ユーティリティ（data.stats.zscore_normalize）
- 設定管理（config.Settings）
  - .env 自動ロード（プロジェクトルート基準）と必須環境変数の検証

## セットアップ手順

前提
- Python 3.10 以上（typing の Union 短縮表記や型注釈を使用）
- pip が利用可能

1. リポジトリをクローン / コピー
   - プロジェクトルートには .git または pyproject.toml を置いてください（.env 自動読み込みで使用）。

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 例（最低限）:
     pip install duckdb defusedxml

   ※ 実運用で Slack 通知や証券会社連携を行う場合は別途ライブラリが必要になることがあります。

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（config.Settings が参照する）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
     - SLACK_BOT_TOKEN: Slack 通知に使用する場合（必須）
     - SLACK_CHANNEL_ID: Slack 通知先（必須）
   - 推奨/デフォルト
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
     - KABU_API_BASE_URL: kabusapi のベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視/モニタ用 SQLite（デフォルト data/monitoring.db）

   例 .env:
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=yyyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

5. DuckDB スキーマ初期化
   - Python で以下を実行:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - ":memory:" を渡すとインメモリ DB が使用できます（テスト向け）。

## 使い方（主要な例）

- DuckDB 初期化
  - from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（市場カレンダー取得、株価、財務の差分ETL、品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)
    print(result.to_dict())

- ファクター・特徴量の作成（features テーブルへ保存）
  - from kabusys.strategy import build_features
    from datetime import date
    count = build_features(conn, date(2024, 1, 5))
    print(f"features upserted: {count}")

- シグナル生成（signals テーブルへ保存）
  - from kabusys.strategy import generate_signals
    from datetime import date
    total = generate_signals(conn, date(2024, 1, 5))
    print(f"signals written: {total}")

- ニュース収集ジョブ（RSS から raw_news を保存、銘柄紐付け）
  - from kabusys.data.news_collector import run_news_collection
    # known_codes は銘柄コードセット（抽出用）
    res = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
    print(res)

- J-Quants 生データ取得（直接利用例）
  - from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
    token = get_id_token()
    records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,5))

- 設定値参照
  - from kabusys.config import settings
    settings.jquants_refresh_token
    settings.duckdb_path
    settings.is_live

注意: 各公開関数は DuckDB 接続を受け取り、ファイル I/O を直接行わない設計の箇所があります。テスト時は in-memory DB を使うと便利です。

## 環境変数と自動ロード挙動
- .env 自動ロード
  - kabusys.config モジュールはプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を探索し、自動で .env / .env.local を読み込みます（OS の環境変数を優先）。自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須変数は Settings のプロパティからアクセスした時に検証され、未設定時は ValueError が発生します。

主な設定キー（環境変数名）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development|paper_trading|live, デフォルト: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)

## ディレクトリ構成（抜粋）
以下は主要なファイル／ディレクトリの構成例（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                       # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py             # J-Quants API クライアント（取得 + 保存ユーティリティ）
    - news_collector.py             # RSS ニュース収集・前処理・DB保存
    - schema.py                     # DuckDB スキーマ定義と init_schema()
    - pipeline.py                   # ETL パイプライン（run_daily_etl 等）
    - stats.py                      # zscore_normalize 等ユーティリティ
    - calendar_management.py        # マーケットカレンダー管理・営業日ユーティリティ
    - audit.py                      # 監査ログ（signal_events / order_requests / executions）
    - features.py                   # data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py            # Momentum/Value/Volatility の計算
    - feature_exploration.py        # 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py        # build_features
    - signal_generator.py           # generate_signals
  - execution/                       # 発注・実行層（実装/拡張用）
    - __init__.py
  - monitoring/                      # 監視・アラート用（存在する場合）
  - その他ドキュメント・テスト等

各ファイルはモジュールレベルで明確な責務を持つよう分割されています（Data / Research / Strategy / Execution 層）。

## 開発・テストのヒント
- DuckDB のインメモリ接続を使うとテストが高速になります（init_schema(":memory:")）。
- jquants_client のネットワーク呼び出しは単体テストではモックしてください（_request, _urlopen 等をモック可能）。
- news_collector のネットワーク部分は内部で SSRF や応答サイズのチェックを行っていますが、ユニットテストでは fetch_rss/_urlopen を差し替えると良いです。
- Settings は .env 自動読み込みを行うため、テスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して明示的に環境変数を注入することを推奨します。

---

追加で README に含めたい項目（使い方の詳細、CI、デプロイ方法、ライセンス、貢献ガイドなど）があれば指定してください。必要に応じてサンプル .env.example やコマンドラインスクリプト例、SQL スキーマ抜粋などを追加できます。