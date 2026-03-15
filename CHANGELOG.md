# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに準拠しています。  
安定したリリースのセマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-15

初回公開リリース。

### 追加 (Added)
- パッケージ基盤を追加
  - pakage: kabusys
  - バージョン: 0.1.0
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境変数 / 設定管理モジュールを追加 (kabusys.config)
  - .env ファイルまたは OS 環境変数からの読み込みをサポート。
  - プロジェクトルート検出機能を実装（.git または pyproject.toml を起点）。
  - 自動ロードの制御:
    - 読み込み順: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動読み込みの無効化が可能（テスト等用）。
  - .env 読み込みの仕様:
    - export KEY=val 形式に対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理、対応する閉じクォートまでを値として扱う。
    - クォートなしの場合、'#' は直前が空白／タブのときのみコメントとして扱う（インラインコメント対応）。
    - ファイル読み込みでエラーが発生した場合は警告を出力して読み込みを継続。
    - OS 環境変数は protected として扱い、上書き制御（override フラグ）を実装。
  - Settings クラスを提供（settings インスタンスを公開）。
    - J-Quants、kabu ステーション、Slack、データベース、システム設定等のプロパティを定義。
    - 必須環境変数取得時に未設定なら ValueError を送出する _require を実装。
    - デフォルト値: KABUSYS_API_BASE_URL 等のデフォルトやデータベースパスの既定値を提供。
    - KABUSYS_ENV (development / paper_trading / live) と LOG_LEVEL の検証を実装。
    - ユーティリティプロパティ: is_live / is_paper / is_dev を提供。

- DuckDB ベースのデータスキーマを追加 (kabusys.data.schema)
  - init_schema(db_path) により DuckDB データベースを初期化し接続を返却。
    - 親ディレクトリが存在しない場合は自動作成。
    - ":memory:" によるインメモリ DB をサポート。
    - 全テーブル・インデックス作成は冪等（存在すればスキップ）。
  - get_connection(db_path) で既存 DB への接続を取得（スキーマ初期化は行わない）。
  - レイヤード設計（Raw / Processed / Feature / Execution）に基づくテーブル群を定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに整合性チェック（CHECK 制約）、主キー、外部キーを定義。
  - パフォーマンスを考慮したインデックス群を作成（銘柄×日付スキャンや status 検索などのクエリパターンを想定）。

- 監査ログ（トレーサビリティ）モジュールを追加 (kabusys.data.audit)
  - 監査用テーブル群（Signal → Order Request → Execution の連鎖）を定義・初期化する API を提供:
    - init_audit_schema(conn): 既存の DuckDB 接続に監査テーブルを追加（冪等）。
      - 全ての TIMESTAMP は UTC で保存するため、初期化時に SET TimeZone='UTC' を実行。
    - init_audit_db(db_path): 監査ログ専用 DB を初期化して接続を返す（親ディレクトリ自動作成対応）。
  - 監査用テーブル:
    - signal_events（戦略が生成したシグナルの記録。棄却やエラーも記録）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ）
      - order_type ごとの CHECK（limit/stop/market に必要／不要な価格フィールドの制約）を実装。
      - 外部キーは ON DELETE RESTRICT（監査ログは削除しない前提）。
      - created_at / updated_at を持ち、アプリ側で updated_at を更新する運用を想定。
    - executions（証券会社からの約定ログ。broker_execution_id を一意キーとして冪等化）
  - 監査テーブル向けのインデックス群を作成（status スキャン、signal_id / order_request_id 結合、broker_order_id 検索等）。

### 変更 (Changed)
- 該当なし（初回リリース）

### 修正 (Fixed)
- 該当なし（初回リリース）

### 注意事項 / 運用メモ
- .env の自動読み込みはプロジェクトルートの検出に依存するため、パッケージ配布後や特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して自動読み込みを無効化し、明示的に環境をセットしてください。
- init_schema / init_audit_db は親ディレクトリを自動作成するため、ファイルパス指定時の権限や配置先に注意してください。
- 監査ログは削除しない設計（ON DELETE RESTRICT）です。データ保持ポリシーに注意して運用してください。
- DuckDB の UNIQUE / NULL の扱い等、RDBMS 固有の挙動に依存する箇所があるため、移行時は挙動確認を行ってください。

--- 
今後のリリースでは、strategy / execution / monitoring の実装、テストカバレッジ、マイグレーション手順、ドキュメント（DataSchema.md, DataPlatform.md）へのリンク付与などを追加予定です。