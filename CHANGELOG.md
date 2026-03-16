KEEP A CHANGELOG
すべての変更は Keep a Changelog の慣例に従って記載します。  
このプロジェクトはセマンティック バージョニングを採用しています。

## [0.1.0] - 2026-03-16
初回リリース。日本株自動売買システムのコアライブラリを実装しました。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - pakage: kabusys
  - バージョンを src/kabusys/__init__.py で "0.1.0" として定義。
  - __all__ に data, strategy, execution, monitoring を公開（strategy と execution のパッケージはプレースホルダとして空の __init__ を含む）。

- 環境設定管理モジュール（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込み（優先順位: OS環境変数 > .env.local > .env）。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）により CWD に依存しない自動ロード。
  - .env の行解析を独自実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープを考慮）。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスで各種設定プロパティを公開:
    - J-Quants / kabuステーション / Slack / DB パス (DuckDB/SQLite) / 環境種別（development/paper_trading/live）/ログレベル検証など。
  - 必須環境変数未設定時に明確なエラーメッセージを送出する _require()。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得機能を実装。
  - レート制御: 固定間隔スロットリングで 120 req/min を厳守する _RateLimiter。
  - リトライロジック: 指数バックオフ、最大 3 回。対象ステータス 408, 429, 5xx。429 の場合 Retry-After ヘッダ優先。
  - 401 受信時は一度だけトークンを自動リフレッシュして再試行（無限再帰を防止）。
  - id_token のモジュールレベルキャッシュ（ページネーション間で共有）。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）:
    - fetched_at を UTC ISO8601 で記録（Look-ahead Bias 対策）。
    - INSERT ... ON CONFLICT DO UPDATE による上書きで重複を排除。
  - 値変換ユーティリティ (_to_float, _to_int) を実装（妥当性チェックを含む）。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - 3 層データモデルに基づくテーブル定義を実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY、CHECK、FOREIGN KEY）およびインデックスを定義。
  - init_schema(db_path) によりディレクトリ自動作成と DDL 実行で初期化（冪等）。
  - get_connection(db_path) で既存 DB への接続を提供。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL を行う run_daily_etl を実装。処理フロー:
    1. 市場カレンダー ETL（先読み lookahead_days）
    2. 株価日足 ETL（差分 + backfill）
    3. 財務データ ETL（差分 + backfill）
    4. 品質チェック（オプション）
  - 差分取得のための補助関数（get_last_price_date, get_last_financial_date, get_last_calendar_date）を提供。
  - backfill_days のデフォルト値設定（3 日）により後出し修正を吸収可能。
  - calendar の取得後に非営業日を直前の営業日に調整する _adjust_to_trading_day。
  - ETLResult データクラスを定義し、取得数・保存数・品質問題・エラー一覧などを返す（to_dict をサポート）。
  - 各ステップは独立してエラーハンドリングされ、1 ステップの失敗でも他ステップは継続（Fail-Fast ではない）。

- 品質チェックモジュール（src/kabusys/data/quality.py）
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - 欠損データ検出（check_missing_data）: raw_prices の OHLC 欄の NULL を検出（severity=error）。
    - スパイク検出（check_spike）: 前日比の絶対変化率が閾値（デフォルト 50%）を超えるレコードを検出。
  - DuckDB を直接利用した効率的な SQL ベースの実装。各チェックは問題を全件収集して返す設計。

- 監査ログ（トレーサビリティ）モジュール（src/kabusys/data/audit.py）
  - シグナル→発注要求→約定のトレーサビリティを確保する監査テーブル群を実装:
    - signal_events, order_requests, executions
  - order_request_id を冪等キーとして利用する設計（再送による二重発注防止）。
  - すべての TIMESTAMP を UTC で扱う（init_audit_schema/set TimeZone='UTC'）。
  - テーブル制約、ステータス遷移、および関連インデックスを定義。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Known behaviors
- .env パースは Bash 互換を完全再現しないため、極端なケースでは差異が発生する可能性がありますが、一般的な export/quote/comment を扱う設計です。
- jquants_client の HTTP 実装は urllib を用いており、運用時のタイムアウトや証明書設定は追加で構成することが可能です。
- strategy と execution のパッケージは存在しますが現時点では初期化子のみ（実装は今後追加予定）。
- audit テーブルは削除を想定しない設計（ON DELETE RESTRICT）で監査証跡を保持します。
- DuckDB の初期化は init_schema を推奨。get_connection はスキーマ作成を行わないため初期化済み DB を渡してください。

### Internal / Developer notes
- テスト容易性のため、jquants_client の関数は id_token を注入可能にしており、API 呼び出しをモックしやすい設計です。
- ログ出力を各モジュールで行っており、運用時の監視やデバッグに役立つ情報を記録します。
- RateLimiter は単純な固定間隔スロットリング実装。より高度なレート制御が必要な場合は拡張を検討してください。

## 今後の予定（例）
- strategy 層の特徴量利用ロジック・バックテスト実装
- execution 層の証券会社接続（kabu ステーション連携）の実装
- 追加の品質チェック（重複・日付不整合検出など）の実装完了と強化
- 単体テスト・統合テストの追加および CI 設定

---