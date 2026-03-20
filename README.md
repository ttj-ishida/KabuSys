# KabuSys

日本株向けの自動売買基盤（研究・データ基盤・戦略・監査を含む）をまとめたライブラリです。  
本リポジトリは次のレイヤーを含みます：データ取得（J-Quants）, ETLパイプライン, DuckDB スキーマ（Raw / Processed / Feature / Execution / Audit）, 研究用ファクター計算、特徴量エンジニアリング、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ。

主な目的は「ルックアヘッドバイアスを防ぎつつ冪等なデータ収集・特徴量生成・シグナル作成」を行い、発注や監査へつなげられる堅牢な基盤を提供することです。

## 機能一覧

- データ層
  - J-Quants API クライアント（ページネーション、レートリミット、リトライ、トークン自動更新）
  - DuckDB 用スキーマ定義と初期化（init_schema）
  - raw / processed / feature / execution / audit 各レイヤのテーブル群
  - RSS ベースのニュース収集（SSRF対策、トラッキングパラメータ除去、記事IDのハッシュ化）
  - カレンダー取得（JPX）と営業日判定ロジック
  - ETL パイプライン（差分取得、バックフィル、品質チェックのフック）

- 研究・戦略層
  - ファクター計算（momentum / volatility / value 等）
  - 特徴量正規化（Zスコア）とユニバースフィルタ
  - シグナル生成（複数ファクター・AIスコア統合、Bearレジーム抑制、BUY/SELL 生成）
  - 研究用ユーティリティ（forward returns, IC, factor summary, ranking）

- オペレーション・監査
  - 発注・約定・ポジションなどの実行層スキーマ
  - 監査ログテーブル（signal_events / order_requests / executions 等）
  - カレンダー更新ジョブ、ニュース収集ジョブなどのユーティリティ関数

- 汎用ユーティリティ
  - .env 読み込み（プロジェクトルート基準、自動ロード可／無効化可）
  - 環境変数管理（必須変数チェック）
  - 小さめの統計ユーティリティ（zscore_normalize など）

## セットアップ手順

※以下は最小限のセットアップ例です。実行環境や CI に合わせて適宜調整してください。

1. 必要条件
   - Python 3.10 以上（| 型アノテーションなどを使用しているため）
   - 標準ライブラリ以外の依存パッケージ（少なくとも）:
     - duckdb
     - defusedxml

2. 仮想環境の作成（例）
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

3. パッケージのインストール
   - pip を最新化して必要パッケージをインストール:
     - pip install -U pip
     - pip install duckdb defusedxml
   - パッケージ化されている場合:
     - pip install -e .

4. 環境変数（.env）
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須となる環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API 用パスワード（発注連携する場合）
     - SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
     - SLACK_CHANNEL_ID — Slack 通知対象チャンネル ID
   - 任意 / デフォルト設定:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - サンプル（.env）:
     - JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     - KABU_API_PASSWORD=your_kabu_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - KABUSYS_ENV=development
     - LOG_LEVEL=INFO

5. データベースの初期化
   - DuckDB のスキーマを初期化します（例）:
     - from kabusys.data.schema import init_schema
       conn = init_schema("data/kabusys.duckdb")

## 使い方（主な操作例）

以下は代表的な API の呼び出し例です。実行は Python スクリプトやジョブランナーから行います。

- DuckDB スキーマ初期化
  - from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（株価・財務・カレンダーを差分取得し品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)
    print(result.to_dict())

- カレンダー更新ジョブ（夜間バッチ）
  - from kabusys.data.calendar_management import calendar_update_job
    saved = calendar_update_job(conn)

- ニュース収集ジョブ（RSS）
  - from kabusys.data.news_collector import run_news_collection
    results = run_news_collection(conn, known_codes={"7203","6758"})  # known_codes を渡すと銘柄紐付けも実施

- 特徴量構築（Feature Engineering）
  - from kabusys.strategy import build_features
    built = build_features(conn, target_date)  # target_date は datetime.date

- シグナル生成
  - from kabusys.strategy import generate_signals
    n_signals = generate_signals(conn, target_date)

- J-Quants データ取得（低レベル）
  - from kabusys.data import jquants_client as jq
    rows = jq.fetch_daily_quotes(date_from=..., date_to=...)

注意点:
- 多くの関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。初回は init_schema() でテーブルを作成してから使用してください。
- ETL / データ保存系は冪等（ON CONFLICT）を前提に実装されています。
- シグナル生成は features / ai_scores / positions テーブルを参照して BUY/SELL を生成します。実装は execution 層に発注処理を直接呼ばない設計です。

## 設定（環境変数の要点）

- 自動で .env を読み込む仕組みがあり、プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から `.env` / `.env.local` を読み込みます。
- 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 必須変数は Settings クラス内でチェックされ、欠けていると ValueError が投げられます。

重要なプロパティ（Settings）:
- settings.jquants_refresh_token
- settings.kabu_api_password
- settings.slack_bot_token
- settings.slack_channel_id
- settings.duckdb_path / settings.sqlite_path
- settings.env （development / paper_trading / live）
- settings.log_level

## ディレクトリ構成

（主要ファイルのみを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得/保存）
    - news_collector.py            — RSS ニュース収集・保存・紐付け
    - schema.py                    — DuckDB スキーマ定義・初期化
    - stats.py                     — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - features.py                  — data レイヤの feature ユーティリティ（再エクスポート）
    - calendar_management.py       — マーケットカレンダー管理 / ジョブ
    - audit.py                     — 監査ログ用スキーマ定義/初期化
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算（momentum / value / volatility）
    - feature_exploration.py       — 研究用分析（forward returns / IC / summary）
  - strategy/
    - __init__.py
    - feature_engineering.py       — ファクター正規化・features テーブル作成
    - signal_generator.py          — final_score 計算と signals 書き込み
  - execution/                      — 発注周り（未使用ファイルが多い場合もある）
  - monitoring/                     — 監視・メトリクス関連（実装に応じて使用）

（ファイルは README 作成時点の主要実装を反映しています）

## 開発／テストのヒント

- 自動環境変数読み込みをテストしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化できます。
- 多くの I/O は duckdb 接続を受けるため、テストでは ":memory:" を渡すことでインメモリ DB を使用できます:
  - conn = init_schema(":memory:")
- ニュース収集や外部 API 呼び出しはネットワーク依存のため、ユニットテストでは jquants_client._request や news_collector._urlopen 等をモックしてください。

---

この README はプロジェクトの主要な使い方・構成をまとめた概要です。より詳細な設計仕様や運用手順（StrategyModel.md, DataPlatform.md, DataSchema.md 等）がリポジトリ内の別ドキュメントにある場合はそちらも参照してください。必要であれば README に追加したいコマンド例や運用フロー（cron / Airflow 等）について追記できます。