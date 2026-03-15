CHANGELOG
=========

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
リリースはセマンティックバージョニング (MAJOR.MINOR.PATCH) に従います。

Unreleased
----------

（現時点では未リリースの変更はありません）

0.1.0 - 2026-03-15
-----------------

Added
- 初回リリースを追加。
- パッケージのエントリポイントを追加。
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を定義し、公開サブパッケージとして data, strategy, execution, monitoring を指定。
- 環境変数/設定管理モジュールを追加（src/kabusys/config.py）。
  - .env ファイルまたは既存の OS 環境変数から設定を読み込む自動ロード機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - プロジェクトルートを __file__ を起点に .git または pyproject.toml で探索して判定するため、CWD に依存しない動作を保障。
  - .env および .env.local の読み込み順序を実装（.env.local は上書き、ただし既存 OS 環境変数は保護）。
  - .env パーサーは以下に対応:
    - 空行・コメント行（#）の無視
    - "export KEY=val" 形式のサポート
    - シングル/ダブルクォートで囲まれた値とバックスラッシュによるエスケープ処理
    - クォート無し値のインラインコメント処理（直前が空白/タブの場合にコメントとみなす）
  - Settings クラスを提供し、アプリケーション設定（J-Quants トークン、kabu API パスワード、Slack トークン・チャンネル、DB パス、環境種別、ログレベル等）をプロパティ経由で安全に取得。環境値検証（KABUSYS_ENV, LOG_LEVEL）を実装。
- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得機能を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - 認証トークン取得関数 get_id_token を実装（refresh token → id token の POST）。
  - API 呼び出し共通処理 _request を実装：
    - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）を実装。
    - リトライロジック（指数バックオフ、最大 3 回）。リトライ対象には 408 / 429 / 5xx／ネットワークエラーを含む。
    - 401 受信時にトークンを自動リフレッシュして 1 回だけ再試行（無限再帰防止のため allow_refresh フラグ）。
    - ページネーション対応（pagination_key の追跡）。
    - JSON デコード失敗時の明確なエラー報告。
  - データを DuckDB に保存するための冪等保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）:
    - ON CONFLICT DO UPDATE による重複回避（冪等性）。
    - PK 欠損の行はスキップしログ出力。
    - fetched_at を UTC ISO 形式で記録し、Look-ahead Bias を防止するため取得時刻のトレーサビリティを提供。
  - データ変換ユーティリティ（_to_float, _to_int）を実装し、安全に数値変換を行う（不正な小数文字列は None を返す等の仕様）。
  - モジュールレベルの ID トークンキャッシュを実装し、ページネーション間でトークンを共有（効率化）。
- DuckDB スキーマ定義・初期化モジュールを追加（src/kabusys/data/schema.py）。
  - DataPlatform 設計に基づく 3 層＋実行層のテーブル定義を実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルにチェック制約（CHECK）や PRIMARY KEY/FOREIGN KEY を設け、データ整合性を確保。
  - 頻出クエリ向けのインデックス群を定義。
  - init_schema(db_path) により、DB ファイルの親ディレクトリ自動作成、DDL の順序考慮による冪等な初期化を実装（:memory: 対応）。
  - get_connection(db_path) を提供（既存 DB への接続）。
- 監査ログ（Audit）モジュールを追加（src/kabusys/data/audit.py）。
  - シグナル→発注→約定のトレーサビリティを UUID チェーンで保持する監査テーブルを実装:
    - signal_events（戦略層の全シグナルログ）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ）
    - executions（証券会社から返る約定ログ、broker_execution_id を冪等キーとして扱う）
  - 全 TIMESTAMP を UTC で保存するため init_audit_schema() 内で SET TimeZone='UTC' を実行。
  - 発注要求に対する詳細なステータス列・検証（limit/stop の price チェック等）を実装。
  - 監査用インデックス群を追加（status ベースのキュー検索や broker_order_id / order_request_id による結合等）。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供（冪等）。
- 空のパッケージプレースホルダを追加:
  - src/kabusys/execution/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/monitoring/__init__.py
  - 将来の機能拡張のためのパッケージ構造を準備。

Changed
- （該当なし：初回リリース）

Fixed
- （該当なし：初回リリース）

Security
- 認証トークンの取り扱いに注意:
  - J-Quants リフレッシュトークンは Settings 経由で取得する設計。環境変数管理（.env/.env.local）によりトークンの取り扱いを容易にするが、本番では安全なシークレット管理を推奨。

Notes / 補足
- すべてのデータ保存処理は冪等性を重視して設計されています（ON CONFLICT ... DO UPDATE）。
- 日時は UTC を基準に扱う方針です（fetched_at / created_at 等）。
- .env の自動ロードはプロジェクトルートの検出に依存します。配布後やパッケージ環境では自動ロードを無効化し、明示的に環境変数を設定することを想定しています。
- strategy, execution, monitoring パッケージは現時点で実装プレースホルダです。今後ここに戦略実装・発注ロジック・監視処理を追加予定。

Contributors
- 初期実装（コードベースに基づく changelog 作成）。