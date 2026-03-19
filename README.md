KabuSys
=======

日本株向けの自動売買基盤ライブラリ（リサーチ・データパイプライン・特徴量生成・シグナル生成・監査／実行層のスキーマ等を含む）

概要
----
KabuSys は日本株のデータ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査用テーブルなどを備えた自動売買基盤のコアライブラリです。DuckDB をデータストアとして利用し、研究（research）・データ（data）・戦略（strategy）・実行（execution）・監視（monitoring）などの層に分かれたモジュール群を提供します。

主な機能
--------
- データ取得/保存
  - J-Quants API クライアント（fetch / save の実装、ページネーション・リトライ・レート制御・トークンリフレッシュ対応）
  - raw_prices / raw_financials / market_calendar / raw_news などの冪等保存（ON CONFLICT）関数
- ETL パイプライン
  - 差分取得（最終取得日から）、バックフィル、品質チェックを含む日次 ETL（run_daily_etl）
- DuckDB スキーマ初期化
  - DataSchema.md に基づく Raw / Processed / Feature / Execution レイヤーのテーブル定義（init_schema）
- 研究（Research）
  - ファクター計算（momentum / volatility / value）と特徴量探索（forward returns / IC / summary）
  - Zスコア正規化ユーティリティ（data.stats.zscore_normalize）
- 特徴量生成 / シグナル生成（Strategy）
  - build_features: 生ファクターの正規化・ユニバースフィルタリング・features テーブルへの UPSERT
  - generate_signals: features と ai_scores を統合して final_score を算出、BUY/SELL を判定して signals テーブルへ登録
- ニュース収集
  - RSS フィード取得、記事正規化、raw_news への冪等保存、銘柄（4桁コード）抽出と紐付け
  - SSRF 対策、gzip サイズ制限、XML の安全パース（defusedxml）
- マーケットカレンダー管理
  - market_calendar の取得/更新、営業日判定・前後営業日・期間内営業日取得など
- 監査ログ（audit）
  - signal_events / order_requests / executions など、発注から約定に至るトレーサビリティを確保するテーブル定義

動作環境 / 依存
----------------
- Python >= 3.10（PEP 604 の | 型等を使用）
- 依存パッケージ（最低限）
  - duckdb
  - defusedxml
- 標準ライブラリ：urllib, logging, datetime, hashlib, socket, ipaddress など

セットアップ手順
----------------

1. リポジトリをクローン（例）
   - git clone <this-repo>

2. （任意）仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ化している場合）pip install -e .

4. 環境変数 / .env の準備
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション等の API パスワード（必須）
     - KABU_API_BASE_URL — kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）
     - DUCKDB_PATH — DuckDB ファイルパス（省略時: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（省略時: data/monitoring.db）
     - KABUSYS_ENV — environment: development | paper_trading | live（省略時: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（省略時: INFO）
   - .env のサンプルを用意して、.env または .env.local を作ってください（.env.local は .env を上書きします）。

使い方（簡単なコード例）
-----------------------

以下はライブラリを使った基本的なワークフロー例です。実行前に .env を適切に設定してください。

- DuckDB スキーマ初期化
  - from kabusys.data.schema import init_schema
  - from kabusys.config import settings
  - conn = init_schema(settings.duckdb_path)

- 日次 ETL の実行（市場カレンダー取得・株価・財務の差分取得・品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)
  - print(result.to_dict())

- 特徴量の構築（build_features）
  - from kabusys.strategy import build_features
  - from datetime import date
  - n = build_features(conn, date(2024, 1, 1))
  - print(f"features upserted: {n}")

- シグナル生成（generate_signals）
  - from kabusys.strategy import generate_signals
  - from datetime import date
  - total = generate_signals(conn, date(2024, 1, 1), threshold=0.6)
  - print(f"signals written: {total}")

- ニュース収集ジョブ（RSS フェッチ -> DB 保存 -> 銘柄紐付け）
  - from kabusys.data.news_collector import run_news_collection
  - known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセット
  - results = run_news_collection(conn, known_codes=known_codes)
  - print(results)

- カレンダー更新バッチ
  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)
  - print(f"calendar saved: {saved}")

コマンド例（python -c を使った一行実行）
- DB 初期化:
  - python -c "from kabusys.config import settings; from kabusys.data.schema import init_schema; init_schema(settings.duckdb_path)"
- 日次 ETL 実行:
  - python -c "from kabusys.config import settings; from kabusys.data.schema import get_connection; from kabusys.data.pipeline import run_daily_etl; conn = get_connection(settings.duckdb_path); print(run_daily_etl(conn).to_dict())"

設計上の注意点 / 動作ポリシー
----------------------------
- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml を基準）から読み込まれます。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API リクエストはレート制御・リトライ・トークン自動リフレッシュを行います（内部で RateLimiter を使用）。
- ETL / DB 書き込みは可能な限り冪等（ON CONFLICT / トランザクション）を意識して実装されています。
- ルックアヘッドバイアス防止のため、各処理は target_date 時点で利用可能なデータのみを使用する方針です。
- RSS の取得は SSRF 対策、gzip サイズ制限、XML の安全パース（defusedxml）等の安全対策を含みます。

ディレクトリ構成（主要ファイル）
------------------------------
(以下は src/kabusys 以下の主要モジュールです。実際のリポジトリにはさらにファイルが存在する可能性があります)

- src/kabusys/
  - __init__.py
  - config.py                         -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py               -- J-Quants API クライアント（fetch/save）
    - pipeline.py                     -- ETL パイプライン（run_daily_etl 等）
    - news_collector.py               -- RSS 収集・保存・銘柄抽出
    - schema.py                       -- DuckDB スキーマ定義・初期化
    - stats.py                        -- z-score 正規化等統計ユーティリティ
    - features.py                     -- data.stats の再エクスポート
    - calendar_management.py          -- market_calendar 管理 / 営業日判定 / 更新ジョブ
    - audit.py                         -- 監査ログ関連 DDL（signal_events 等）
  - research/
    - __init__.py
    - factor_research.py              -- momentum / volatility / value の計算
    - feature_exploration.py          -- forward returns / IC / summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py          -- build_features
    - signal_generator.py             -- generate_signals
  - execution/
    - __init__.py                      -- 実行層プレースホルダ（発注ラッパ等を想定）
  - monitoring/                         -- monitoring を想定（__all__ に含まれるが実装は用途により拡張）

ライセンス・貢献
----------------
- この README はコードベースのドキュメント要約です。実運用時はテスト・コードレビュー・セキュリティ監査を行ってください。
- 貢献ルールやライセンスはリポジトリの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

トラブルシューティング
----------------------
- .env が読み込まれない / テスト時に読み込みを抑止したい:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB に接続できない / パスの作成に失敗する:
  - settings.duckdb_path を確認し、親ディレクトリが存在しない場合は init_schema が自動的に作成しますが、パーミッション等を確認してください。
- J-Quants の認証エラー (401) が出る:
  - JQUANTS_REFRESH_TOKEN が正しいか、またはネットワーク回復後に自動リフレッシュが行われるかログを確認してください。

付記
----
ここに記載したサンプルや手順はライブラリの公開 API に基づく最小限の利用例です。実運用でのジョブスケジューリング、ログ集約、監査、リトライ戦略、発注前のリスクチェックや資金管理ロジックなどは別途実装してください。