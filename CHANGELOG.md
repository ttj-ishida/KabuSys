# Changelog

すべての注目すべき変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠しており、セマンティックバージョニングに従います。

## [Unreleased]

(なし)

## [0.1.0] - 2026-03-16

初回公開リリース。日本株自動売買基盤のコア機能を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基本情報
  - kabusys パッケージ初期化とバージョン定義（src/kabusys/__init__.py）。

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。読み込み順序は OS 環境変数 > .env.local > .env。
  - プロジェクトルート検出機能を導入（.git または pyproject.toml を探索）。
  - .env パーサーは export 形式、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 自動ロード無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境 / ログレベルなどの設定を型安全に取得。値検証（KABUSYS_ENV, LOG_LEVEL）を実施。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得関数を実装（ページネーション対応）。
  - レート制限対応（固定間隔スロットリング、デフォルト 120 req/min）。
  - 冪等性と堅牢性のためのリトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
  - 401 Unauthorized 受信時の自動トークンリフレッシュ（1 回まで）を実装し、ページネーション間でトークンを共有するモジュール内キャッシュを保持。
  - 取得データに fetched_at（UTC ISO8601）を付与して Look-ahead Bias を防止。
  - DuckDB へ保存する save_* 関数（save_daily_quotes、save_financial_statements、save_market_calendar）を実装し、ON CONFLICT DO UPDATE による冪等保存を実現。
  - 型変換ユーティリティ（_to_float/_to_int）を実装し、異常値・空値を安全に扱う。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - DataPlatform アーキテクチャに基づく多層スキーマを定義（Raw / Processed / Feature / Execution）。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw 層テーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed 層テーブルを定義。
  - features, ai_scores 等の Feature 層テーブルを定義。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution 層テーブルを定義。
  - 性能改善のためのインデックス群を定義。
  - init_schema(db_path) によりディレクトリ自動作成を含め初期化可能。get_connection() で既存 DB に接続可能。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 日次 ETL のエントリポイント run_daily_etl を実装。処理順はカレンダー取得 → 株価差分取得（バックフィル対応） → 財務差分取得 → 品質チェック。
  - 差分取得ロジック：DB の最終取得日時を基に未取得範囲のみを自動算出し、デフォルトで backfill_days=3 により後出し修正を吸収。
  - カレンダーは lookahead_days=90 の先読み取得を行い、営業日調整に使用。
  - ETLResult データクラスを導入し、取得件数、保存件数、品質問題、エラーを集約。品質問題は詳細を含む辞書化が可能。
  - 各ステップは独立してエラーハンドリングされ、あるステップのエラーが他ステップの実行を阻害しない設計（Fail-Fast ではない）。

- 品質チェックモジュール (src/kabusys/data/quality.py)
  - データ品質チェック基盤を実装。チェックは SQL を用いて効率的に実行し、複数の問題を収集する設計。
  - 実装済みチェック：
    - 欠損データ検出（raw_prices の OHLC 欠損を検出し QualityIssue を返す）
    - スパイク検出（前日比の変動率が閾値を超えるレコードを検出）
  - QualityIssue データクラスを導入（check_name, table, severity, detail, rows）。
  - check 関数はサンプル行（最大 10 件）を返すため、監査/通知に利用できる。

- 監査ログ (Audit) モジュール (src/kabusys/data/audit.py)
  - シグナルから約定までの完全トレーサビリティを提供する監査用テーブルを実装。
  - テーブル：signal_events, order_requests（冪等キー order_request_id を使用）, executions（証券会社約定ID を一意扱い）を定義。
  - テーブルとインデックスの初期化関数 init_audit_schema(conn) / init_audit_db(db_path) を提供。
  - すべての TIMESTAMP は UTC を使用する方針（初期化時に SET TimeZone='UTC' を実行）。
  - 発注・約定の状態遷移・制約（チェック制約や外部キー）を明確化。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 注意事項 / マイグレーション
- .env の自動読み込みはデフォルトで有効です。テスト等で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 初期化時は init_schema() を使ってスキーマを作成してください。監査ログは init_audit_schema() / init_audit_db() で追加してください。
- J-Quants API の認証には JQUANTS_REFRESH_TOKEN を環境変数で設定する必要があります（Settings.jquants_refresh_token）。
- run_daily_etl は品質チェックで検出した問題を自動で止めない設計です。重大な品質問題で ETL を停止したい場合は呼び出し側で ETLResult の内容を評価してください。

### セキュリティ (Security)
- なし（初回リリース）

---

今後のリリースでは、次のような改善を計画しています（例）:
- 監査ログへのアプリ側更新操作ユーティリティ（order_request のステータス遷移ヘルパー等）
- 追加の品質チェック（重複検出、将来日付・営業日外データ検出）
- strategy / execution 層の具体的実装（発注インターフェース、ブローカ抽象化）
- CI 用のテストヘルパー（ID トークンのモック注入・HTTP クライアントの抽象化）

質問や改善希望があればお知らせください。