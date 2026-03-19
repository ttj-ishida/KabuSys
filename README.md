# KabuSys

日本株向け自動売買システム用ライブラリ（軽量コア）。  
本リポジトリはデータ取得・ETL、特徴量計算、リサーチユーティリティ、監査用スキーマ等を提供します。実際の発注／ブローカー連携やフロントエンドは別モジュールで実装する想定です。

## プロジェクト概要
KabuSys は以下の目的を持つモジュール群を含みます。
- J-Quants API から市場データ（株価・財務・市場カレンダー）を取得して DuckDB に保存する ETL パイプライン
- ニュース（RSS）収集と記事→銘柄の紐付け処理
- DuckDB スキーマ定義（Raw / Processed / Feature / Execution / Audit）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 研究・ファクター計算ユーティリティ（モメンタム、ボラティリティ、バリュー等）
- 監査ログ（signal → order → execution のトレースを保証）

設計上のポイント：
- DuckDB を中心に軽量かつ冪等（ON CONFLICT）を重視
- J-Quants API 呼び出しはレートリミット・リトライ・トークン自動リフレッシュ対応
- RSS 収集は SSRF / XML Bomb 等に対する安全対策を実装
- 外部依存を最小に（標準ライブラリでの実装を志向）ただし DuckDB などは必須

## 主な機能一覧
- データ取得 / 保存
  - J-Quants から日足（OHLCV）、四半期財務、JPX カレンダーを取得（jquants_client）
  - 取得データを DuckDB の raw_* テーブルへ冪等保存（save_* 関数群）
- ETL パイプライン
  - 差分取得（最終取得日からの差分）とバックフィル機能（data.pipeline.run_daily_etl など）
  - 市場カレンダー先読み
- ニュース収集
  - RSS フェード収集、前処理、記事ID生成（正規化 URL → SHA256）、raw_news 保存、銘柄抽出・紐付け
- データ品質チェック
  - 欠損、スパイク検出、重複、日付不整合（data.quality.run_all_checks）
- スキーマ管理
  - DuckDB 用の詳細なスキーマ定義と初期化（data.schema.init_schema）
  - 監査ログ（audit.init_audit_schema / init_audit_db）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー計算（research.factor_research）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー（research.feature_exploration）
  - Zスコア正規化（data.stats.zscore_normalize）

## 前提（Requirements）
- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- （任意）J-Quants API 利用には有効なリフレッシュトークンが必要

必要なパッケージは pyproject.toml / requirements に定義されている想定です。最小限は上記をご準備ください。

## セットアップ手順

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. インストール
   - 開発環境であればプロジェクトルートで:
     pip install -e ".[dev]"  （pyproject に extras が定義されている場合）
   - 最小依存だけインストールする場合:
     pip install duckdb defusedxml

3. 環境変数設定
   - プロジェクトルートに .env を作成するか、OS 環境変数を設定してください。
   - 必須の環境変数（config.Settings に基づく）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD     : kabu ステーション API 用パスワード（必須）
     - SLACK_BOT_TOKEN       : Slack Bot トークン（必須）
     - SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
   - 任意・デフォルト
     - KABUSYS_ENV           : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH           : 監視用 SQLite パス（デフォルト data/monitoring.db）
   - .env 自動読み込み
     - .env / .env.local がプロジェクトルートにある場合、config モジュールが自動的に読み込みます。
     - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトで以下を実行して DB を初期化します。
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)
     ```
   - 監査ログ専用 DB を初期化する場合:
     ```python
     from kabusys.data.audit import init_audit_db
     conn_audit = init_audit_db("data/audit.duckdb")
     ```

## 使い方（主要な例）

- 日次 ETL 実行（J-Quants から取得 → DuckDB に保存 → 品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  # known_codes: 銘柄抽出に使う有効コードのセット（例: {"7203", "6758"}）
  stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
  print(stats)
  ```

- ファクター計算（モメンタム例）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  records = calc_momentum(conn, target_date=date(2024, 1, 31))
  # records は各銘柄ごとの mom_1m, mom_3m, mom_6m, ma200_dev を含む dict のリスト
  ```

- 将来リターン・IC 計算（リサーチ用）
  ```python
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
  # factor_records は自前で計算したファクターリスト（各要素に "code" とファクター列を含む）
  fwd = calc_forward_returns(conn, target_date=date(2024,1,31), horizons=[1,5,21])
  ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

- カレンダー更新ジョブ（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print("saved calendar rows:", saved)
  ```

- 監査スキーマを既存接続へ追加
  ```python
  from kabusys.data.audit import init_audit_schema
  conn = init_schema(settings.duckdb_path)
  init_audit_schema(conn, transactional=True)
  ```

## 環境変数（まとめ）
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルト値あり）:
- KABUSYS_ENV (development|paper_trading|live) — default: development
- LOG_LEVEL (DEBUG|INFO|...) — default: INFO
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（任意）

.env ファイルのパースはシェル風（export KEY=val、クォート、コメント）に対応しています。

## ディレクトリ構成
主要なファイル / モジュールと簡単な説明:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（アプリ設定）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py        — RSS 取得 / 前処理 / 保存 / 銘柄抽出
    - schema.py                — DuckDB スキーマ定義・初期化（init_schema）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - features.py              — 特徴量に関する公開インターフェース
    - calendar_management.py   — 市場カレンダー管理・ユーティリティ
    - audit.py                 — 監査ログ（signal/order/execution）スキーマ初期化
    - etl.py                   — ETLResult の公開（エイリアス）
    - quality.py               — データ品質チェック（欠損・スパイク等）
    - stats.py                 — 汎用統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py              — 研究用ユーティリティの再エクスポート
    - factor_research.py       — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py   — 将来リターン/IC/統計サマリー
  - strategy/
    - __init__.py              — 戦略層（拡張用プレースホルダ）
  - execution/
    - __init__.py              — 発注・実行管理（拡張用プレースホルダ）
  - monitoring/
    - __init__.py              — 監視・アラート（拡張用プレースホルダ）

（上記は現状実装済みモジュールの概要です。strategy / execution / monitoring は基盤を想定した空モジュールが配置されています）

## 注意事項 / 運用上のポイント
- J-Quants API はレート制限（120 req/min）に従う必要があります。本クライアントは固定間隔スロットリングと指数バックオフで制御しますが、運用時は十分なスリープ/スケジューリングを検討してください。
- ETL は差分取得＋バックフィル方式で API 側の後出し修正に対応する設計です。
- ニュース収集は外部 URL にアクセスするため SSRF / XML 攻撃に対する保護を施しています。それでも運用環境ではネットワークポリシーを適切に設定してください。
- DuckDB スキーマは多くの制約チェックとインデックスを定義します。初回のスキーマ作成は時間がかかる場合があります。

## 貢献 / 拡張
- strategy や execution 層を実装して発注フローを完成させることが想定されます。
- 研究・特徴量モジュールは追加ファクターや機械学習モデルの統合に適しています。
- テストの追加、CI の整備、詳しいドキュメント（DataPlatform.md / StrategyModel.md）を参照して拡張してください。

---

この README はリポジトリ内のコードの現状を基に作成しています。運用時は pyproject.toml や別途付属するドキュメント（.env.example, DataPlatform.md 等）があればそちらも参照してください。