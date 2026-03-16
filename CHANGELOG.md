# Changelog

すべての変更は Keep a Changelog の仕様に準拠し、重要なリリースはセマンティックバージョニングに従います。

注: この CHANGELOG は与えられたコードベースの内容から推測して作成しています。

## [Unreleased]

### Added
- （今後の変更をここに記載）

---

## [0.1.0] - 2026-03-16

初回公開リリース。日本株自動売買システム "KabuSys" のコア機能を実装しました。主要な追加点は以下の通りです。

### Added
- パッケージ基礎
  - パッケージバージョン管理を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージの公開モジュールを __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート自動検出機能を追加（.git または pyproject.toml を基準に探索）。
  - .env と .env.local の自動読み込みを実装（.env.local が .env を上書き）。
  - 自動ロード無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト等で利用可能）。
  - .env のパースロジックを強化:
    - export KEY=val 形式対応
    - シングル／ダブルクォート、バックスラッシュエスケープ対応
    - インラインコメントの取り扱い（クォート有無に応じた判別）
    - 上書き禁止（protected）キーのサポート（OS環境変数を保護）
  - 必須環境変数取得時の検証（未設定で ValueError を発生）。
  - 設定値のバリデーション:
    - KABUSYS_ENV（development / paper_trading / live）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - DB パス設定（DuckDB / SQLite）の取得ユーティリティ。

- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API から以下データを取得する機能を実装:
    - 株価日足（OHLCV）
    - 財務データ（四半期 BS/PL）
    - JPX マーケットカレンダー（祝日・半日・SQ）
  - API 呼び出しユーティリティを実装:
    - レート制限（120 req/min）に基づく固定間隔スロットリング（_RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 受信時に refresh（1 回のみ）して再試行する自動トークン更新。
    - ページネーション対応（pagination_key の追跡）。
    - id_token のモジュールレベルキャッシュ（ページネーション間で共有）。
    - JSON デコードエラー時の詳細メッセージ。
    - fetched_at を UTC タイムスタンプで記録して Look-ahead Bias を抑制。
  - DuckDB に対する冪等保存処理を提供:
    - save_daily_quotes / save_financial_statements / save_market_calendar：ON CONFLICT DO UPDATE による重複排除と更新。
    - PK 欠損行はスキップし、スキップ数をログ出力。
  - 型変換ユーティリティ（_to_float / _to_int）を実装し、弱い入力に耐性を持たせる。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義を追加:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに CHECK 制約・PRIMARY KEY を定義してデータ整合性を担保。
  - 頻出クエリを想定したインデックスを作成。
  - init_schema(db_path) でディレクトリ作成・テーブル作成を行う初期化関数を提供（冪等）。
  - get_connection(db_path) により既存 DB へ接続可能。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新を行う ETL パイプラインを実装:
    - 最終取得日を基に date_from を自動算出（backfill_days により後出し修正を吸収）。
    - 市場カレンダーは lookahead により未来分を先読みして営業日判定に利用。
    - 各取得は独立してエラーハンドリングし、1 ステップ失敗でも他を継続する設計。
    - id_token 注入によりテスト容易性を確保。
  - run_prices_etl / run_financials_etl / run_calendar_etl を実装（フェッチ→保存→ログ）。
  - run_daily_etl により一括 ETL（カレンダー → 株価 → 財務 → 品質チェック）を実行。
  - ETL 実行結果を表す ETLResult dataclass を追加（品質問題・エラーの集約、シリアライズ可）。
  - 市場カレンダーがある場合の営業日調整ヘルパーを実装（_adjust_to_trading_day）。

- 監査ログ（Audit）モジュール（src/kabusys/data/audit.py）
  - シグナル→発注→約定までのトレーサビリティを確保する監査テーブルを実装:
    - signal_events（戦略シグナルログ）
    - order_requests（発注要求、order_request_id を冪等キーとして利用）
    - executions（証券会社からの約定ログ、broker_execution_id を一意キーとして冪等性確保）
  - すべての TIMESTAMP を UTC で保存するように初期化時に SET TimeZone='UTC' を実行。
  - 状態遷移（pending → sent → filled / partially_filled / cancelled / rejected / error）を設計に明示。
  - 監査用インデックスを定義して検索・結合性能を向上。
  - init_audit_schema / init_audit_db を提供（既存接続へ追記や専用 DB 初期化が可能）。

- データ品質チェック（src/kabusys/data/quality.py）
  - QualityIssue dataclass を定義し、各チェックで検出した問題を構造化して返却。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損（open/high/low/close）を検出し、サンプル行を返却。
    - check_spike: 前日比でスパイク（急騰・急落）を LAG ウィンドウ関数で検出（閾値パラメータ対応）。
  - チェックは Fail-Fast にせず全件を収集する設計で、呼び出し元（ETL）が重大度に応じて判断可能。
  - DuckDB での効率的な SQL 実行とパラメータバインドを使用。

### Changed
- （初回リリースのため履歴なし）

### Fixed
- （初回リリースのため履歴なし）

### Security
- （初回リリースで特記事項なし）

---

## 既知の設計／実装ポイント（ドキュメント的注記）
- .env パーサは多くの現実的ケース（クォート、エスケープ、export プレフィックス、コメント等）に対応する一方で、本番運用でのパーシング境界や特殊ケースについては追加の実運用テストが推奨されます。
- J-Quants クライアントは 120 req/min を想定した固定間隔レート制御を行います。高スループットが必要な場合は実運用でのチューニングが必要です（例えば並列化制御やバースト許容設定など）。
- データ品質チェックは欠損・スパイクの主要チェックを実装済み。重複チェックや日付不整合チェックは設計に明記されており、追加実装を行いやすい構造になっています。
- DuckDB を用いたスキーマは冪等に作成されるため既存データベースへのマイグレーションや追記が可能ですが、実運用ではバックアップ/マイグレーション手順の確立を推奨します。

---

参照:
- 各種実装は src/kabusys 以下のモジュールに含まれます（config.py / data/jquants_client.py / data/schema.py / data/pipeline.py / data/audit.py / data/quality.py）。