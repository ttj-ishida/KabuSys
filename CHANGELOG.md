# CHANGELOG

すべての重要な変更点はこのファイルに記録します。本ドキュメントは「Keep a Changelog」フォーマットに準拠します。

全般ルール:
- バージョン番号はパッケージの __version__ に従います。
- 日付はこの変更履歴作成日です。

## [Unreleased]


## [0.1.0] - 2026-03-16

初回リリース。日本株自動売買システムのコアデータ層、ETL、監査、品質チェック、設定管理、J-Quants API クライアントを実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化を定義（kabusys.__init__）。公開モジュール: data, strategy, execution, monitoring。
  - バージョン: 0.1.0

- 環境設定管理 (`kabusys.config`)
  - .env ファイルと OS 環境変数からの自動ロード機能を実装。
  - プロジェクトルート検出ロジック: `.git` または `pyproject.toml` を基準に親ディレクトリを検索（CWD 依存を回避）。
  - .env パーサー: `export KEY=val` 形式、シングル/ダブルクォート、エスケープシーケンス、コメント処理に対応。
  - 自動ロードの無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - Settings クラスを提供し、アプリケーションで使用する主要な設定値をプロパティ経由で取得（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、環境 / ログレベル判定など）。
  - 設定値のバリデーション（KABUSYS_ENV / LOG_LEVEL の有効値チェック）および必須項目未設定時のエラー (`_require`)。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得機能を実装（ページネーション対応）。
  - API 呼び出しの共通実装: レートリミッタ、リトライ（指数バックオフ、最大 3 回）、HTTP ステータスに基づくリトライ制御（408/429/5xx 等）。
  - 401 Unauthorized 時にリフレッシュトークンから ID トークンを自動取得して 1 回リトライ（無限再帰を防止）。
  - モジュールレベルの ID トークンキャッシュでページネーション間のトークン共有を実現。
  - JSON デコード失敗時や HTTP エラー時の詳細な例外メッセージ。
  - DuckDB への保存関数: `save_daily_quotes`, `save_financial_statements`, `save_market_calendar` を提供。いずれも冪等（ON CONFLICT DO UPDATE）で保存し、`fetched_at` を UTC タイムスタンプで記録。
  - 値変換ユーティリティ `_to_float`, `_to_int`（堅牢な変換、空値処理、小数文字列の扱いに注意）。

- DuckDB スキーマ定義・初期化 (`kabusys.data.schema`)
  - DataPlatform の 3 層（Raw / Processed / Feature）＋ Execution 層を網羅する DDL を定義。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed テーブル。
  - features, ai_scores などの Feature テーブル。
  - signals, signal_queue, orders, trades, positions, portfolio_performance などの Execution テーブル。
  - パフォーマンス向けに想定クエリに基づくインデックスを作成。
  - `init_schema(db_path)` によりディレクトリ生成 → DuckDB 接続 → 全テーブル・インデックス作成（冪等）。
  - `get_connection(db_path)` による既存 DB への接続取得。

- ETL パイプライン (`kabusys.data.pipeline`)
  - 日次 ETL の主要ロジックを実装: カレンダー取得 → 株価差分取得（バックフィル対応）→ 財務データ差分取得 → 品質チェック。
  - 差分更新ヘルパー: DB の最終取得日から自動で再取得範囲を算出（デフォルト backfill_days=3）。
  - カレンダーは先読み（デフォルト 90 日）を行い、非営業日のターゲット調整機能を実装。
  - fetch/save は jquants_client の idempotent な保存関数を利用。
  - 品質チェック（quality モジュール）をオプションで実行。ETL はステップ毎にエラーハンドリングされ、1 ステップ失敗でも他ステップは継続。
  - ETL 実行結果を表す `ETLResult` クラスを提供（品質問題・エラーメッセージの集約、シリアライズ機能）。

- 監査ログ（トレーサビリティ）(`kabusys.data.audit`)
  - シグナル → 発注要求 → 約定までの監査テーブルを実装。
  - テーブル: `signal_events`, `order_requests`（冪等キー: order_request_id）, `executions`（broker_execution_id はユニーク）。
  - すべての TIMESTAMP を UTC で保存する方針を採用（init 時に `SET TimeZone='UTC'` を実行）。
  - 監査用インデックス群を作成し、クエリパフォーマンスを向上。
  - `init_audit_schema(conn)` と `init_audit_db(db_path)` を提供。

- データ品質チェック (`kabusys.data.quality`)
  - 必須カラムの欠損検出（`check_missing_data`）: raw_prices の OHLC 欠損を検出しサンプルを返す。
  - スパイク検出（`check_spike`）: 前日比変動率が閾値（デフォルト 50%）を超えるレコードを検出（LAG ウィンドウを使用）。
  - 問題は `QualityIssue` dataclass として集約（check_name, table, severity, detail, rows）。
  - 各チェックは Fail-Fast せず、問題を列挙して返す設計（呼び出し元が重大度に応じて停止判断）。

### 変更 (Changed)
- 初回リリースにあたって多数のモジュールを新規追加したため、外部仕様（API、DB スキーマ、環境変数名など）は以降のリリースで拡張・変更される可能性があります。

### 修正 (Fixed)
- 初版のため特定のバグ修正履歴はありません。実運用でのフィードバックにより修正予定。

### 既知の制約 / 注意点 (Notes)
- 自動 .env ロードはプロジェクトルートが検出できない場合はスキップされます（配布後の動作を想定）。
- J-Quants API のレート制限は 120 req/min に固定した実装（固定間隔スロットリング）。高スループット用途では設計の見直しが必要になる可能性あり。
- ID トークンの自動リフレッシュは 401 を受けた場合に「最大 1 回」行う挙動です。リフレッシュ失敗時はエラーになります。
- DuckDB スキーマの DDL は多くの制約・CHECK を含むため、データロード時に型・値の整合性に注意してください。
- audit テーブルは削除を前提としない（ON DELETE RESTRICT 等）監査用途向けの設計。

### 互換性に関する注記 (Breaking Changes)
- なし（初回リリース）。

---

将来的なリリースでは、strategy と execution 層の具体的な発注実装、モニタリング、Slack 連携等の機能追加・改善を予定しています。問題報告・機能要望は Issue にてお願いします。