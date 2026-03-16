CHANGELOG
=========

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
-------------

- なし

0.1.0 - 2026-03-16
------------------

Added
- 初回リリース。パッケージ名: kabusys（__version__ = 0.1.0）。
- 基本パッケージ構成を追加:
  - kabusys.config: 環境変数・設定管理
    - .env / .env.local の自動ロード機能（プロジェクトルートを .git または pyproject.toml で検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメントをサポート。
    - Settings クラスで各種必須設定をプロパティ提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パスなど）。
    - KABUSYS_ENV と LOG_LEVEL の入力検証（有効値制約）。
  - kabusys.data.jquants_client: J-Quants API クライアント
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得機能を実装（ページネーション対応）。
    - API レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）。
    - 再試行（指数バックオフ、最大 3 回）、対象ステータスコードの扱い（408, 429, >=500）。
    - 401 Unauthorized を検出した際の自動トークンリフレッシュ（1 回のみ）と id_token キャッシュ。
    - JSON デコード失敗やネットワークエラーの取り扱い、Retry-After ヘッダ優先のロジック。
    - DuckDB に保存する際の idempotent な save_* 関数（ON CONFLICT DO UPDATE を使用）。
    - 取得時刻（fetched_at）は UTC タイムスタンプで記録し、Look-ahead Bias 対策を考慮。
    - 型変換ユーティリティ (_to_float, _to_int) を実装。float->int 変換時の小数部チェックなど安全な変換を行う。
  - kabusys.data.schema: DuckDB スキーマ定義・初期化
    - Raw / Processed / Feature / Execution の 3 層＋監査用テーブルを定義。
    - 各テーブルの制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）を定義。
    - 検索を高速化するためのインデックス群を作成。
    - init_schema(db_path) によりディレクトリ作成とテーブル作成を行う（冪等）。
    - get_connection() を提供（既存 DB への接続）。
  - kabusys.data.pipeline: ETL パイプライン
    - 日次 ETL のエントリポイント run_daily_etl() を実装（カレンダー、株価、財務、品質チェック）。
    - 差分更新ロジック: DB の最終取得日を参照し、backfill_days による先戻しで API 後出し修正を吸収。
    - 市場カレンダーは lookahead（デフォルト 90 日）で先読みして営業日調整に利用。
    - 各ステップは独立してエラーハンドリング（1 ステップの失敗でも他ステップは継続）。
    - ETLResult クラスで実行結果・品質問題・エラーを集約して返却。
  - kabusys.data.quality: データ品質チェック
    - 欠損データ検出（OHLC 欄の欠損）、スパイク検出（前日比閾値で検出）、重複・日付不整合の検出を想定した設計。
    - QualityIssue データクラスで問題を集約。Fail-Fast ではなく全件収集して呼び出し元で判定できる方式。
    - DuckDB 接続を使用した SQL ベースの効率的チェック実装。
  - kabusys.data.audit: 監査ログ / トレーサビリティ
    - シグナル→発注要求→約定までを追跡する監査用テーブルを定義（signal_events, order_requests, executions）。
    - order_request_id を冪等キーとして二重発注防止を想定。
    - すべての TIMESTAMP は UTC 保存（init_audit_schema は SET TimeZone='UTC' を実行）。
    - 発注・実行のステータス列や整合性チェック、必要なインデックスを追加。
  - その他
    - パッケージの __all__ と空の execution/strategy パッケージプレースホルダを追加（将来的な拡張準備）。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Deprecated
- なし

Removed
- なし

Security
- なし（ただし機密情報は .env または環境変数により管理する想定。kabusys.config の protected ロジックで既存 OS 環境変数を保護）。

注記（利用上の注意・マイグレーション）
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings の各プロパティを参照）。
  - 自動ロードはデフォルトで有効。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- J-Quants API:
  - レート制限（120 req/min）・リトライ方針に従うため、短時間に大量リクエストを行うとスロットリングされる可能性あり。
  - トークンリフレッシュ処理は自動化されているが、失敗時は例外が発生する。
- DuckDB:
  - init_schema() は冪等。初回実行で必要ディレクトリを自動作成する。
  - 監査テーブルを別 DB に分けたい場合は init_audit_db() を利用。
- ETL:
  - run_daily_etl() はカレンダー取得後に対象日を営業日に調整するため、カレンダー未取得時はフォールバック挙動あり。
  - 品質チェックで検出された問題は ETLResult.quality_issues に集約され、呼び出し元の判断で処理を停止するか通知するかを選べる。
- 型変換:
  - _to_int は "1.0" のような文字列を int に変換できるが、"1.9" のように小数部が残る場合は None を返すなど、安全設計。

今後の予定（短期）
- execution / strategy / monitoring の具体実装の追加（発注実行、戦略ロジック、監視アラート等）。
- 追加の品質チェック（重複・将来日付チェック等）の実装とテストカバレッジ拡充。
- 単体テスト／統合テストと CI 設定の追加。

もし特定のリリースノート形式（例えば英語表記、詳細なコミット対応など）や、項目の追加・修正希望があれば教えてください。