# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。本プロジェクトは Keep a Changelog の慣習に従います。  
参照フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

---

## [0.1.0] - 2026-03-16

初回リリース。本リリースでは日本株自動売買プラットフォームの基盤となる設定管理、データ取得・保存、ETLパイプライン、データ品質チェック、監査ログ（トレーサビリティ）、および DuckDB スキーマを提供します。

### Added（追加）
- パッケージの初期化
  - src/kabusys/__init__.py にてパッケージ情報を公開（__version__ = 0.1.0、サブパッケージを __all__ に列挙）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動ロードする仕組みを実装。
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env のパーサを実装（export 形式、シングル/ダブルクォート、エスケープ、行内コメントの取り扱いに対応）。
  - Settings クラスを提供し、アプリケーション設定（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等）をプロパティで取得可能。
    - 必須項目は _require で検証して未設定時に説明付きの ValueError を送出。
    - KABUSYS_ENV の検証（development / paper_trading / live のみ許容）。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する API クライアントを実装。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - レート制限対応（固定間隔スロットリング）を実装し、デフォルトで 120 req/min を守る（_RateLimiter）。
  - 再試行ロジックを実装（指数バックオフ、最大 3 回、ステータス 408/429 と 5xx を再試行対象）。
  - 401 を受けた場合は ID トークンを自動リフレッシュして 1 回リトライ（トークンキャッシュ共有）。
  - get_id_token（リフレッシュトークンから idToken を取得）を実装。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。
    - 保存処理は冪等（INSERT ... ON CONFLICT DO UPDATE）で重複や再実行に耐える。
    - fetched_at を UTC ISO8601 形式で記録し、いつデータを取得したかトレース可能に。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層に対応した詳細な DDL を実装。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 頻出クエリ向けのインデックスを定義（code×date や status 等）。
  - init_schema(db_path) でディレクトリ作成→テーブル・インデックス作成を行い、接続を返す（冪等）。
  - get_connection(db_path) で既存 DB へ接続。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL（run_daily_etl）を実装。処理は以下の順で実行される：
    1. 市場カレンダー ETL（先読み; デフォルト lookahead 90 日）
    2. 株価日足 ETL（差分 + backfill、デフォルト backfill_days=3）
    3. 財務データ ETL（差分 + backfill）
    4. 品質チェック（quality モジュール、オプション）
  - 差分更新ロジックを実装（DB の最終取得日から未取得分のみ取得、最小取得日は 2017-01-01）。
  - ETLResult データクラスを導入し、各種統計（取得件数・保存件数・品質問題・エラー）を返却。
  - 各ステップは独立してエラーハンドリングされ、1 ステップの失敗が他を止めない設計。

- データ品質チェック（src/kabusys/data/quality.py）
  - QualityIssue データクラスを導入。
  - チェック実装:
    - 欠損データ検出: raw_prices の OHLC 欄の NULL を検出（check_missing_data）
    - スパイク検出: 前日比が閾値（デフォルト 50%）を超える急騰／急落を検出（check_spike）
    - （設計上）重複チェック、日付不整合検出などを想定 / 拡張可能
  - 各チェックはサンプル行（最大 10 件）を返し、Fail-Fast ではなく全件収集する方針。

- 監査ログ・トレーサビリティ（src/kabusys/data/audit.py）
  - 戦略→シグナル→発注要求→約定へと続く監査用テーブル（signal_events, order_requests, executions）を定義。
  - UUID ベースの冪等キー（order_request_id 等）によるトレースと二重発注防止を想定。
  - 全 TIMESTAMP は UTC で保存するよう init_audit_schema() で SET TimeZone='UTC' を実行。
  - init_audit_db(db_path) で監査専用 DB の初期化を提供。
  - ステータス列、各種チェック制約、インデックスを用意し検索性能と整合性を向上。

- ユーティリティ関数
  - jquants_client 内の _to_float / _to_int などの変換ユーティリティ（空文字や異常値に安全に対応）。
  - pipeline の _adjust_to_trading_day（非営業日を直近の営業日に調整）を実装。
  - schema と audit の初期化は parent ディレクトリ自動作成に対応。

### Changed（変更）
- （初回リリースのため該当なし）

### Fixed（修正）
- （初回リリースのため該当なし）

### Security（セキュリティ）
- センシティブ情報は環境変数経由で取得する設計（.env 利用時もローカル環境に配置）。
- .env 自動読み込みは環境変数で無効化可能（テスト環境の安全性確保）。
- SQL 実行時はパラメータバインド（?）を利用する方針（pipeline/quality モジュール参照）。

### Notes / Known limitations（注意・既知の制限）
- ネットワーク I/O は同期的（urllib）に実行されるため、大量リクエスト時はプロセスのブロッキングが発生します。将来的に非同期化の検討が可能。
- レートリミッタは単一プロセス内での固定間隔スロットリングであり、マルチプロセスや分散実行時は外部レート制御（トークンバケット等）や API 側のレート管理との調整が必要です。
- jquants_client の再試行ポリシーは一般的なバックオフを実装していますが、用途によってはより細かなカスタマイズ（最大リトライ回数の調整等）が必要になります。
- 現在の品質チェックは代表的なものを実装しており、運用に応じてチェック項目の追加・閾値調整が必要です。

---

今後のリリースでは、戦略実装（strategy パッケージ）、注文送信とブローカー連携（execution パッケージ）、監視（monitoring）およびより詳細な品質チェックとテストカバレッジの追加を予定しています。