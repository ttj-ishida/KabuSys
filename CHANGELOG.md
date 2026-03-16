# Changelog

すべての重要な変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

現在のリリースポリシー: セマンティックバージョニング (MAJOR.MINOR.PATCH)

## [Unreleased]
（現時点のコードベースは最初の公開バージョンとして 0.1.0 を含みます。今後の変更はここに記載します）

## [0.1.0] - 2026-03-16

初回リリース。日本株自動売買システム「KabuSys」のコアデータ層・設定・ETL・監査機能を実装しました。

### Added
- パッケージ基盤
  - src/kabusys/__init__.py にパッケージ情報（バージョン、公開モジュール一覧）を追加。
- 設定・環境変数管理
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルートは .git / pyproject.toml を基準に探索）。
    - .env パースの堅牢化: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応。
    - 自動読み込みを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - OS 環境変数を保護する protected ロジック（.env.local で既存 OS 環境変数を上書きしない）。
    - 必須設定取得用の _require と Settings クラスを提供（J-Quants トークン、kabu API、Slack、DB パス等のプロパティ、値検証含む）。
    - KABUSYS_ENV と LOG_LEVEL の妥当性検証（development/paper_trading/live、DEBUG/INFO/...）。
- J-Quants クライアント
  - src/kabusys/data/jquants_client.py
    - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得 API 呼び出し（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - ページネーション対応（pagination_key に基づく繰り返し取得）。
    - レート制限（120 req/min）を守る固定間隔スロットリングの実装（内部 RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）。429 の場合は Retry-After ヘッダを尊重。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ共有化（ページネーション間で共有）。
    - JSON デコード失敗時の明示的エラーメッセージ。
    - DuckDB へ冪等的に保存する save_daily_quotes / save_financial_statements / save_market_calendar を実装（ON CONFLICT DO UPDATE）。
    - データ型変換ユーティリティ (_to_float, _to_int) を実装。float/整数文字列の扱い・不正値の安全化を考慮。
    - データ取得時の fetched_at を UTC ISO8601 で記録（Look-ahead bias 防止のため）。
- DuckDB スキーマ・初期化
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution の 3 層（＋監査用テーブル）に基づく詳細な DDL を定義。
    - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
    - features, ai_scores 等の Feature テーブル。
    - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブル。
    - 各種制約（主キー、チェック制約、外部キー）とパフォーマンス用インデックスを定義。
    - init_schema(db_path) により DuckDB ファイルの親ディレクトリ自動作成とテーブル作成を行う（冪等）。
    - get_connection(db_path) で既存 DB への接続を提供（初期化は行わない）。
- ETL パイプライン
  - src/kabusys/data/pipeline.py
    - 日次 ETL の実装（run_daily_etl）:
      - マーケットカレンダー ETL → 株価 ETL → 財務 ETL → 品質チェック の順。
      - 各ステップは独立してエラーハンドリングされ、1 ステップの失敗でも他ステップを継続（エラーは収集して戻す）。
      - 差分取得ロジック: DB の最終取得日を参照し、backfill_days を考慮して差分更新。
      - カレンダーの先読み（デフォルト 90 日）と営業日調整（非営業日は直近営業日に調整）。
      - run_prices_etl, run_financials_etl, run_calendar_etl を個別に実行可能。
      - ETL 実行結果を ETLResult データクラスで返却（品質問題とエラーの詳細を含む）。
- 監査ログ（トレーサビリティ）
  - src/kabusys/data/audit.py
    - signal_events / order_requests / executions の監査用テーブルを定義（UUID ベースのトレースチェーンを考慮）。
    - 発注の冪等化（order_request_id）・制約（limit/stop/market のチェック）を明示。
    - すべての TIMESTAMP を UTC 保存する設定（init_audit_schema は SET TimeZone='UTC' を実行）。
    - init_audit_schema(conn) / init_audit_db(db_path) API を提供。
    - 監査用インデックス群を定義（status や日付・銘柄での検索を想定）。
- データ品質チェック
  - src/kabusys/data/quality.py
    - 欠損データ検出（open/high/low/close の NULL 検出）: check_missing_data
    - スパイク（前日比）検出: check_spike（デフォルト閾値 50%）
    - QualityIssue データクラスによる問題の表現（check 名、テーブル、severity、サンプル行を含む）
    - SQL ベースで効率的にチェックを実行し、Fail-Fast とせず全件収集する方針。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- API トークン（J-Quants）の取り扱い：
  - refresh_token は Settings 経由で環境変数から取得。get_id_token の実行は明示的に行う設計（自動漏洩防止）。
  - .env 読み込み時に OS 環境変数を保護する仕組みを追加（上書きされない）。

### Notes / Implementation details
- 冪等性:
  - DuckDB への保存は ON CONFLICT DO UPDATE を採用しており、重複挿入による不整合を防止。
- レート制限と再試行:
  - J-Quants API は 120 req/min の想定。固定間隔スロットリングと指数バックオフの組合せで安全に API を叩く設計。
- 品質チェックの扱い:
  - 品質チェックで重大（error）な問題が検出された場合でも、ETL は自動的に中断せず結果に問題を含めて返却。運用側で判断してアラートや再処理を行う想定。
- 時刻の取り扱い:
  - 監査ログや fetched_at 等は UTC で保存する方針。
- 可観測性:
  - 主要処理（fetch / save / ETL の各段階）で logger を使用して情報・警告・例外ログを出力。

---

その他、今後追加予定事項（例）
- 長期運用でのパフォーマンス改善（大規模データのパーティショニング等）
- strategy / execution / monitoring 層の実装強化（現状はパッケージ骨組みのみ）
- 単体テスト・統合テストの追加（外部 API モック化を含む）
- エラー通知（Slack 等）やメトリクス公開（Prometheus 等）

もし CHANGELOG に追加してほしい項目（より詳細な機能説明、担当者、コミット参照など）があれば教えてください。