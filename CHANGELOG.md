CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

[0.1.0] - 2026-03-16
-------------------

Added
- 初回公開: KabuSys 日本株自動売買システム (バージョン 0.1.0)
  - パッケージエントリポイント
    - src/kabusys/__init__.py: パッケージ名と __version__、公開モジュール一覧（data, strategy, execution, monitoring）。
  - 設定・環境変数読み込み
    - src/kabusys/config.py
      - .env ファイルおよび環境変数から設定値を読み込む自動ローダ実装（プロジェクトルートの検出は .git / pyproject.toml を基準）。
      - 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数を上書きしない保護処理を実装。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化に対応（テスト用）。
      - .env パーサー (_parse_env_line) が以下をサポート:
        - export KEY=val 形式
        - シングル/ダブルクォート内のバックスラッシュエスケープ
        - インラインコメントの適切な扱い（クォートあり/なしで挙動を区別）
      - Settings クラスによる型付き・検証付きアクセスプロパティ:
        - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須 (未設定時は ValueError を送出)
        - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値
        - KABUSYS_ENV の検証（development, paper_trading, live）
        - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
        - is_live / is_paper / is_dev のユーティリティプロパティ
  - データアクセス・ETL 基盤 (DuckDB)
    - src/kabusys/data/schema.py
      - Raw / Processed / Feature / Execution の 3 層 + 監査用テーブルを想定した DuckDB DDL を定義。
      - raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance を作成。
      - 各種制約（PRIMARY KEY, CHECK 等）とパフォーマンス用インデックスを定義。
      - init_schema(db_path) により冪等的にスキーマ作成と接続を返す（parent ディレクトリ自動作成、":memory:" サポート）。
      - get_connection(db_path) を提供（既存 DB 接続）。
  - J-Quants API クライアント
    - src/kabusys/data/jquants_client.py
      - /token/auth_refresh による ID トークン取得 (get_id_token) とトークンキャッシュ実装（ページネーション間で共有）。
      - レート制限: 固定間隔スロットリング実装 (_RateLimiter) でデフォルト 120 req/min を遵守。
      - 再試行ロジック: 指数バックオフ、最大 3 回、対象ステータス (408, 429, >=500)。
      - 401 受信時はトークンを自動リフレッシュして最大 1 回リトライ（無限再帰防止）。
      - ページネーション対応の取得関数:
        - fetch_daily_quotes (OHLCV)
        - fetch_financial_statements (四半期 BS/PL)
        - fetch_market_calendar (JPX 市場カレンダー)
      - DuckDB への保存関数（冪等）:
        - save_daily_quotes, save_financial_statements, save_market_calendar
        - 保存時に fetched_at を UTC で記録、INSERT ... ON CONFLICT DO UPDATE による更新。
      - ユーティリティ関数: _to_float / _to_int による安全な型変換（空値・不正値を None に変換）。
  - 監査ログ（トレーサビリティ）
    - src/kabusys/data/audit.py
      - signal_events / order_requests / executions の DDL を定義。
      - order_requests は冪等キー (order_request_id) を持ち、limit/stop の価格チェック等の CHECK 制約を実装。
      - 約定（executions）は broker_execution_id をユニークとして外部系の冪等性を保持。
      - init_audit_schema(conn) / init_audit_db(db_path) を提供。UTC タイムゾーン強制 (SET TimeZone='UTC')。
      - 監査用インデックス定義（status 検索や signal_id など）。
  - データ品質チェック
    - src/kabusys/data/quality.py
      - QualityIssue データクラスを定義（チェック名、テーブル、重大度、サンプル行等）。
      - チェック実装:
        - check_missing_data: raw_prices の OHLC 欄欠損検出（volume は対象外）
        - check_duplicates: raw_prices の主キー重複検出
        - check_spike: 前日比スパイク（デフォルト閾値 50%）検出（LAG を使用）
        - check_date_consistency: 将来日付・market_calendar と矛盾する非営業日データ検出
      - run_all_checks により全チェックをまとめて実行し、検出結果をリストで返す。各チェックは複数の問題を収集（Fail-fast ではない）。
  - モジュール骨格
    - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py を追加（パッケージ構成の雛形）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 注意事項
- 必須環境変数が未設定の場合、Settings のプロパティ呼び出し時に ValueError が発生します（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
- .env 読み込みはプロジェクトルートが見つからない場合はスキップされます（パッケージ配布後の挙動を考慮）。
- J-Quants クライアントは urllib を用いた簡易実装で、接続タイムアウトやエラー処理を実装しています。必要に応じて requests 等の HTTP ライブラリへの差し替えや単体テスト（モック）を推奨します。
- DuckDB スキーマは厳密な CHECK 制約を多用しています。外部から直接データを投入する場合は制約違反に注意してください。
- 監査ログは削除しない前提の設計（ON DELETE RESTRICT）になっています。運用でのデータ保持方針に注意してください。

今後の改善案（未実装）
- J-Quants クライアントの単体テスト・モックや統合テストの追加
- strategy / execution / monitoring の具体実装（現在はモジュール骨格）
- より細かなログメトリクスとモニタリング（SLACK 通知の実装連携）
- データ品質チェックの自動アラート化（閾値管理 UI など）
- HTTP クライアントの堅牢化（接続プール・タイムアウト調整・メトリクス収集）

Contributors
- 初期実装: 開発チーム

--- 

（以後の変更はバージョンごとに上に追記してください）