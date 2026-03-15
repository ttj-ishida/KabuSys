# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計された Python パッケージです。J-Quants 等の外部データソースから市場データを取得し、DuckDB に蓄積、特徴量抽出・戦略・発注監査までを想定した基盤モジュール群を提供します。

このリポジトリはコアモジュール（設定管理、データ取得・スキーマ、監査ログ、戦略・実行インターフェース等）を含んでおり、ユーザの戦略ロジックやブローカー接続を実装して組み合わせることで自動売買システムを構築できます。

主な特徴
- 環境変数ベースの設定管理（.env / .env.local 自動読み込み、無効化オプションあり）
- J-Quants API クライアント
  - 日足（OHLCV）/ 財務データ / JPX マーケットカレンダー取得
  - レート制限（120 req/min）遵守、指数バックオフによるリトライ、401 時の自動トークンリフレッシュ
  - ページネーション対応、fetched_at による取得時刻トレーサビリティ
- DuckDB ベースのスキーマ定義（Raw / Processed / Feature / Execution レイヤ）
  - 冪等な INSERT（ON CONFLICT DO UPDATE）で重複を排除
- 監査ログ（signal → order_request → execution のトレーサビリティ用スキーマ）
- 軽量な API（設定：config.Settings、データ：data.schema / data.jquants_client、監査：data.audit）

セットアップ手順（開発向け・最小限）
1. 必要な Python バージョン
   - Python 3.10 以上を推奨（| 型注釈等を使用）

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - このリポジトリで必要な外部依存は主に duckdb（標準ライブラリのみで HTTP は urllib を使用）。プロジェクトルートに requirements.txt がない場合は最低限以下をインストールしてください：
     - pip install duckdb

   - 開発中はパッケージを編集可能モードでインストール：
     - pip install -e .

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に .env を置くと、自動で読み込まれます（優先順位：OS 環境 > .env > .env.local。 .env.local は上書きされます）。
   - 自動読み込みを無効化する場合：
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env に設定すべき主なキー（例）
- JQUANTS_REFRESH_TOKEN=<あなたの J-Quants リフレッシュトークン>  (必須)
- KABU_API_PASSWORD=<kabuステーション API パスワード>            (必須)
- KABU_API_BASE_URL=http://localhost:18080/kabusapi             (任意、デフォルトあり)
- SLACK_BOT_TOKEN=<Slack Bot Token>                            (必須)
- SLACK_CHANNEL_ID=<Slack Channel ID>                          (必須)
- DUCKDB_PATH=data/kabusys.duckdb                               (任意、既定値)
- SQLITE_PATH=data/monitoring.db                                (任意、既定値)
- KABUSYS_ENV=development|paper_trading|live                    (任意、デフォルト: development)
- LOG_LEVEL=INFO|DEBUG|WARNING|ERROR|CRITICAL                   (任意、デフォルト: INFO)

.env のパースは POSIX 風の書式をサポートします（export プレフィックス、シングル/ダブルクォート、# コメントの扱い等）。

使い方（簡単な例）
- 設定にアクセスする
  - from kabusys.config import settings
  - settings.jquants_refresh_token / settings.duckdb_path / settings.env などを参照可能

- DuckDB スキーマの初期化
  - from kabusys.data.schema import init_schema
  - conn = init_schema(settings.duckdb_path)
  - init_schema(":memory:") でインメモリ DB を利用可能

- J-Quants から日足取得して保存する（概念例）
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  - from kabusys.data.schema import init_schema
  - conn = init_schema(settings.duckdb_path)
  - records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
  - saved = save_daily_quotes(conn, records)

- ID トークンの明示取得（必要に応じて）
  - from kabusys.data.jquants_client import get_id_token
  - id_token = get_id_token()  # settings.jquants_refresh_token を使用して取得

- 監査ログテーブルの初期化
  - from kabusys.data.audit import init_audit_schema, init_audit_db
  - conn = init_schema(settings.duckdb_path)
  - init_audit_schema(conn)
  - または専用 DB を作る: audit_conn = init_audit_db("data/audit.duckdb")

実装上のポイント（開発者向けメモ）
- jquants_client:
  - レート制限 120 req/min を固定間隔スロットリングで制御
  - リトライ: 最大 3 回（408 / 429 / 5xx を対象）、指数バックオフ
  - 401 受信時はリフレッシュトークンから id_token を再取得して 1 回だけリトライ
  - ページネーションの pagination_key を使って全件取得
  - 取得データの fetched_at を UTC で付与し、Look-ahead Bias の防止に寄与
- データ保存:
  - raw_* テーブルへの保存は ON CONFLICT DO UPDATE により冪等化
- config:
  - プロジェクトルートを .git または pyproject.toml から自動検出して .env を読み込む（CWD に依存しない）
  - 重要な環境変数は settings のプロパティ経由で取得し、未設定時には ValueError を投げる
- audit:
  - signal → order_request → execution を UUID 連鎖で追跡可能にする監査用テーブル群を提供
  - すべての TIMESTAMP は UTC 保存を前提（init_audit_schema は SET TimeZone='UTC' を実行）

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py  — パッケージ初期化、__version__
  - config.py    — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存ロジック）
    - schema.py         — DuckDB スキーマ定義・初期化（Raw/Processed/Feature/Execution）
    - audit.py          — 監査ログ（signal / order_request / executions）定義・初期化
  - strategy/
    - __init__.py       — 戦略モジュールのエントリ（拡張ポイント）
  - execution/
    - __init__.py       — 発注・ブローカー連携のエントリ（拡張ポイント）
  - monitoring/
    - __init__.py       — 監視用モジュール（拡張ポイント）

補足 / 注意事項
- セキュリティ
  - .env に機密情報（トークン・パスワード）を保存する場合、リポジトリにコミットしないでください。.gitignore に .env を含めることを推奨します。
- テスト/CI
  - 自動テストや CI で .env の自動読み込みを避けたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 実運用
  - settings.is_live / is_paper / is_dev を活用して、本番（live）とペーパー（paper_trading）で挙動を分岐させてください。
  - 発注周り（execution モジュール）はブローカー API 実装に依存するため、必ず冪等性・監査ログの保存・エラーハンドリングを厳格に行ってください。

ライセンスや貢献方法などの記載が必要な場合はプロジェクトルートに別途追記してください。

以上がこのコードベースの概要と導入方法です。特定の機能の使い方（例: duckdb スキーマの拡張、戦略モジュール実装、kabuステーション連携のサンプル等）について詳しいサンプルを作成したい場合は、必要なユースケースを教えてください。