# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
初回リリース（バージョンはパッケージ内部の __version__ に合わせています）。

<!-- 改行 -->

## [0.1.0] - 2026-03-16

### 追加 (Added)
- 基本パッケージ構成を追加
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`。
  - パッケージ公開モジュール: `data`, `strategy`, `execution`, `monitoring`。

- 環境変数・設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出ロジック（`.git` または `pyproject.toml` を基準）を実装し、CWD に依存しない自動ロードを実現。
  - .env のパース機能を充実（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理等に対応）。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用途など）。
  - 必須設定取得ヘルパー `_require()` と `Settings` クラスを提供。
  - 主な設定プロパティ:
    - J-Quants 関連: `jquants_refresh_token`
    - kabuステーション: `kabu_api_password`, `kabu_api_base_url`（デフォルト http://localhost:18080/kabusapi）
    - Slack: `slack_bot_token`, `slack_channel_id`
    - DB パス: `duckdb_path`（デフォルト `data/kabusys.duckdb`）、`sqlite_path`（デフォルト `data/monitoring.db`）
    - 実行環境 `env`（`development`, `paper_trading`, `live` の検証）と `log_level` の検証
    - 補助プロパティ: `is_live`, `is_paper`, `is_dev`

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 日次株価（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得するクライアントを実装。
  - レート制限サポート: 固定間隔スロットリング（120 req/min）を実装（内部 `_RateLimiter`）。
  - リトライ戦略: 指数バックオフ（最大 3 回）、対象ステータス (408, 429, 5xx) をリトライ、429 の場合は `Retry-After` を尊重。
  - 401 発生時はリフレッシュトークンで ID トークンを自動更新して 1 回リトライ（無限再帰防止のため `allow_refresh` を制御）。
  - ページネーション対応の取得処理（`pagination_key` を追跡して重複を防止）。
  - データ取得時に「取得時刻（fetched_at）」を UTC で付与して Look-ahead バイアス対策を支援。
  - DuckDB への冪等保存関数を提供（ON CONFLICT DO UPDATE を利用）:
    - `save_daily_quotes`, `save_financial_statements`, `save_market_calendar`
  - 型変換ユーティリティ `_to_float`, `_to_int` を搭載（安全な変換と異常値の扱い）。

- DuckDB スキーマ定義と初期化 (`kabusys.data.schema`)
  - DataPlatform 設計に基づく多層スキーマを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの制約（PRIMARY KEY, CHECK 等）を定義してデータ整合性を強化。
  - 主要なインデックスを作成（銘柄×日付検索やステータス検索に最適化）。
  - スキーマ初期化関数:
    - `init_schema(db_path)`：ディレクトリ自動作成、冪等的に DDL とインデックスを作成して `duckdb` 接続を返す。
    - `get_connection(db_path)`：既存 DB への接続を返す（スキーマ初期化は行わない）。

- ETL パイプライン (`kabusys.data.pipeline`)
  - 日次 ETL のメインエントリポイント `run_daily_etl` を実装（カレンダー → 株価 → 財務 → 品質チェックの順）。
  - 差分更新ロジックを導入:
    - DB の最終取得日を参照して未取得分のみを取得。
    - デフォルトで「バックフィル 3 日（backfill_days）」を行い、API の後出し修正を吸収。
    - カレンダーは先読み（デフォルト 90 日）して営業日調整に使用。
  - 個別ジョブ関数:
    - `run_prices_etl`, `run_financials_etl`, `run_calendar_etl`（各々取得→保存→ログ）。
  - 品質チェックの結果や処理中のエラーを集約する `ETLResult` を導入（監査ログや運用判断に利用）。
  - 各ステップは独立して例外ハンドリング。1ステップ失敗でも残りのステップを継続して全問題を収集する設計（Fail-Fast ではない）。

- 監査ログ（トレーサビリティ） (`kabusys.data.audit`)
  - シグナルから約定に至るトレーサビリティのための監査スキーマを実装:
    - `signal_events`（戦略が生成したシグナルの記録）
    - `order_requests`（発注要求、order_request_id を冪等キーとして利用、注文タイプに応じた CHECK 制約あり）
    - `executions`（証券会社から返された約定ログ、broker_execution_id を一意キーとして扱う）
  - 全 TIMESTAMP を UTC 保存（`SET TimeZone='UTC'` を初期化時に実行）。
  - インデックス群を定義して日付・銘柄検索やステータススキャンを最適化。
  - 初期化 API:
    - `init_audit_schema(conn)`：既存の DuckDB 接続に監査テーブルを追加。
    - `init_audit_db(db_path)`：監査専用 DB を初期化して接続を返す。

- データ品質チェック (`kabusys.data.quality`)
  - 欠損データ検出（OHLC 欠損）、スパイク（前日比 ±X%）検出、重複、日付不整合などのチェック実装方針を確立。
  - `QualityIssue` データクラスを導入し、チェック名・テーブル・重大度・詳細・サンプル行を返す統一インタフェースを提供。
  - チェック実装例:
    - `check_missing_data(conn, target_date)`：raw_prices の OHLC 欠損を検出（サンプル最大 10 件を返す、発見時は severity="error"）。
    - `check_spike(conn, target_date, threshold)`：LAG ウィンドウを用いて前日比が閾値を超えるレコードを検出。  
  - ETL パイプラインから呼び出し可能で、重大度に応じた運用判断を可能にする。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 既知の留意点 (Notes / Known issues)
- J-Quants クライアントは標準ライブラリの urllib を使用しているため、複雑な HTTP 要求（セッション管理・高機能なリトライ等）が必要な場合は将来的に requests 等への置換を検討してください。
- `_to_int` は "1.9" のような小数表現は意図しない切り捨てを避けるため None を返す設計です。上位での扱いに注意してください。
- DuckDB の UNIQUE / NULL の扱いなど、データベースエンジン固有の挙動に依存する箇所があります（例: UNIQUE INDEX と NULL の扱い）。
- 自動 .env ロードはプロジェクトルート検出に依存するため、配布後や特殊な配置では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して手動で設定を注入することを推奨します。

### 開発者向けメモ (Developer Notes)
- 主要な導入点:
  - DB 初期化: from kabusys.data.schema import init_schema; conn = init_schema(settings.duckdb_path)
  - 監査スキーマ初期化: from kabusys.data.audit import init_audit_schema; init_audit_schema(conn)
  - 日次 ETL 実行: from kabusys.data.pipeline import run_daily_etl; result = run_daily_etl(conn)
  - API クライアント直接利用: from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token 等
  - 設定参照: from kabusys.config import settings; settings.jquants_refresh_token 等
- ロギング・例外ハンドリングは各モジュールで行われているため、運用時はログ出力レベルとログ蓄積先を適切に設定してください。

---

今後のリリースでは以下を検討:
- strategy / execution / monitoring モジュールの具体実装（現状はパッケージプレースホルダ）
- テスト用のモック注入改善（HTTP クライアント抽象化）
- 高度な監視・メトリクス（Prometheus 等）や運用用 CLI の追加
- J-Quants API の仕様変更に追随するためのバージョニングと互換性レイヤ

（以上）