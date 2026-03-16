# Changelog

すべての非互換変更はここに記載します。本ファイルは「Keep a Changelog」準拠で、安定したリリース履歴を残すことを目的とします。

注: 以下の変更内容は提供されたコードベースから推測して記載しています。

## [0.1.0] - 2026-03-16

初回リリース

### 追加 (Added)
- パッケージの基本構成を追加
  - パッケージ名: kabusys (`src/kabusys/__init__.py`)、バージョン `0.1.0`
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ にて公開

- 環境設定モジュールを追加 (`src/kabusys/config.py`)
  - .env ファイル自動読み込み機能（プロジェクトルートは .git または pyproject.toml で検出）
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - .env パーサーで以下に対応:
    - 空行 / コメント行スキップ、`export KEY=VAL` 形式対応
    - シングル/ダブルクォートのエスケープ処理
    - インラインコメントの扱い（クォートあり/なしの違いを考慮）
  - 環境変数取得ヘルパ `_require` と、Settings クラスによるプロパティ取得:
    - J-Quants / kabu / Slack / DB パスなどの設定プロパティを提供
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）
    - DB パスは Path 型で返却（expanduser 対応）
    - is_live / is_paper / is_dev 補助プロパティ

- J-Quants API クライアントを追加 (`src/kabusys/data/jquants_client.py`)
  - API 呼び出しの共通処理 `_request` を実装
    - レート制限（固定間隔スロットリング、120 req/min）
    - 再試行ロジック（指数バックオフ, 最大 3 回、408/429/5xx をリトライ対象）
    - 401 受信時の自動トークンリフレッシュ（1 回まで）とトークンキャッシュ共有
    - ページネーション対応（pagination_key）
    - JSON デコードエラー検出
  - 認証ヘルパ `get_id_token`（リフレッシュトークンから ID トークンを取得）
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等：ON CONFLICT DO UPDATE）:
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - 型変換ユーティリティ `_to_float` / `_to_int`（空値や不正値を None に扱う等）

- DuckDB スキーマ定義と初期化を追加 (`src/kabusys/data/schema.py`)
  - Raw / Processed / Feature / Execution 層に対応したテーブル DDL を定義
  - 主要テーブル（raw_prices, raw_financials, market_calendar, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）を作成
  - 監査やクエリ性能を考慮したインデックスを定義
  - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成後、全テーブル・インデックスを冪等に作成
  - get_connection(db_path) で既存 DB への接続を取得（初期化は行わない）

- ETL パイプラインを追加 (`src/kabusys/data/pipeline.py`)
  - 日次 ETL の主要設計を実装
    - 差分更新（DB の最終取得日を基に自動で date_from を計算）
    - backfill_days による再取得（API の後出し修正対応、デフォルト 3 日）
    - カレンダーの先読み（デフォルト 90 日）
    - 各 ETL ステップは独立してエラーハンドリング（1 ステップ失敗でも他ステップは継続）
    - id_token の注入可能（テスト容易性）
  - 個別ジョブ:
    - run_prices_etl, run_financials_etl, run_calendar_etl（各差分 ETL）
  - 統合エントリ:
    - run_daily_etl（カレンダー → 株価 → 財務 → 品質チェックの順で実行）
  - ETLResult データクラス:
    - 各種取得/保存件数、品質チェック結果、エラーリストを保持
    - has_errors / has_quality_errors / to_dict を提供

- データ品質チェックモジュールを追加 (`src/kabusys/data/quality.py`)
  - QualityIssue データクラス（check_name, table, severity, detail, rows）
  - 各チェックを実装（DuckDB SQL を使用）
    - check_missing_data: raw_prices の OHLC 欄の欠損検出（サンプル最大 10 件）
    - check_spike: 前日比スパイク検出（LAG を利用、閾値はデフォルト 50%）
    - （設計に重複チェック・日付不整合も記載。コード中での実装の続きに依存）
  - 品質チェックは Fail-Fast ではなくすべての問題を収集して返す設計

- 監査（トレーサビリティ）テーブルを追加 (`src/kabusys/data/audit.py`)
  - トレーサビリティ階層（business_date → strategy_id → signal_id → order_request_id → broker_order_id）設計
  - テーブル:
    - signal_events（戦略が生成したシグナル。棄却やエラーも記録）
    - order_requests（発注要求。order_request_id を冪等キーとして利用、入力チェックあり）
    - executions（証券会社からの約定情報、broker_execution_id を冪等キーとして扱う）
  - すべての TIMESTAMP を UTC で保存（init 関数内で TimeZone を UTC に設定）
  - init_audit_schema(conn) と init_audit_db(db_path) を提供（冪等）
  - 監査用インデックス群を定義（status・signal_id・broker_order_id 等による検索高速化）

### 変更 (Changed)
- 当初リリースのため該当なし（初版のため、主要な設計と機能を追加）

### 修正 (Fixed)
- 当初リリースのため該当なし

### 注意点 / 実装上の設計方針（ドキュメント的説明）
- 冪等性: DuckDB への書き込みは ON CONFLICT DO UPDATE を用いて再実行可能な設計。
- レート制御と堅牢性: J-Quants へのアクセスは固定間隔の RateLimiter、リトライ（指数バックオフ）、401 発生時のトークン自動リフレッシュにより堅牢に実装。
- テスト容易性: id_token 注入や .env 自動読み込みの無効化オプションによりユニットテストを想定。
- トレーサビリティ: 監査用スキーマは削除しない前提で設計（ON DELETE RESTRICT 等）。
- 時刻管理: すべての監査 TIMESTAMP は UTC を前提とする（init_audit_schema で TimeZone をセット）。

### 既知の制約 / 将来的な改善候補
- quality モジュール内の全チェック実装の進捗によっては追加のチェックが必要（重複チェックや日付不整合検出等）。
- 外部 API（J-Quants）から返るデータ形式の変化に対するさらなる堅牢化（スキーマ検証やスキーマバージョン管理）が考えられる。
- duckdb の UNIQUE / NULL の扱いに起因する制約やインデックス運用の最適化は運用を通じて調整が必要。

---

今後のリリースでは、strategy / execution / monitoring 層の実装、テストカバレッジ、CI 用の DB モック・フェイク実装、より詳しい DataPlatform / DataSchema ドキュメントの同梱を予定してください。