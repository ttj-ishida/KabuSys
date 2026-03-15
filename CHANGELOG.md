CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- 変更はカテゴリ別（Added, Changed, Fixed, Deprecated, Removed, Security）に記載します。
- バージョンは semantic versioning を想定しています。

[Unreleased]
-------------

なし

0.1.0 - 2026-03-15
------------------

初回公開リリース。日本株自動売買システムのコア基盤を実装しました。主な追加内容は以下のとおりです。

Added
- パッケージのエントリポイントを追加
  - kabusys.__init__ に __version__="0.1.0" と __all__ を定義。
- 環境設定管理モジュール (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD に依存しない）。
  - .env パース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを抑止可能。
  - Settings クラスを実装し、必須設定の取得（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）や各種既定値（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV）を提供。
  - 環境値検証: KABUSYS_ENV および LOG_LEVEL の妥当性チェック。
- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX カレンダーを取得する関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - ページネーション対応（pagination_key を利用、ループで全件取得）。
  - レート制限実装: 固定間隔スロットリングで 120 req/min を遵守する _RateLimiter。
  - リトライ/バックオフ: 指定ステータス（408, 429, >=500）やネットワークエラーに対して指数バックオフで最大 3 回リトライ。
  - 401 ハンドリング: トークン期限切れ検知時に id_token を自動リフレッシュして 1 回リトライ（無限再帰防止のため allow_refresh フラグ）。
  - id_token のモジュールレベルキャッシュ実装（ページネーション間で共有可能）。
  - JSON レスポンスのデコードチェックと適切な例外処理。
  - データ取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を防止するためのトレーサビリティを確保。
  - DuckDB へ保存するユーティリティ関数を追加（save_daily_quotes, save_financial_statements, save_market_calendar）。いずれも冪等性を担保（INSERT ... ON CONFLICT DO UPDATE）。
  - 型変換ユーティリティ (_to_float, _to_int) を実装し、不正値に対して安全に None を返す。
- DuckDB スキーマ定義・初期化モジュール (kabusys.data.schema)
  - DataPlatform.md に基づく 3 層（Raw / Processed / Feature）および Execution 層のテーブル DDL を整備。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等を定義（Processed）。
  - features, ai_scores 等の Feature 層を定義。
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等の Execution 層を定義。
  - テーブル間の制約（PRIMARY KEY, FOREIGN KEY, CHECK 条件）を豊富に付与してデータ整合性を担保。
  - よく使われるクエリパターン向けのインデックスを多数作成。
  - init_schema(db_path) により DuckDB を初期化して接続を返す機能を提供（親ディレクトリの自動作成、:memory: 対応）。
  - get_connection(db_path) による接続取得（スキーマ初期化は行わない）。
- 監査ログ（トレーサビリティ）モジュール (kabusys.data.audit)
  - シグナルから約定に至る一連の監査テーブルを実装（signal_events, order_requests, executions）。
  - order_request_id を冪等キーとして扱う設計（重複送信防止）。
  - すべての TIMESTAMP を UTC で扱う方針を採用（init_audit_schema で SET TimeZone='UTC' を実行）。
  - 状態遷移やデータ保持方針（削除しない、ON DELETE RESTRICT）等の設計原則を反映。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。
- パッケージ構成の雛形
  - kabusys.data.__init__, kabusys.execution.__init__, kabusys.strategy.__init__, kabusys.monitoring.__init__ を配置（将来の拡張ポイント）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / 実装上の注意
- .env の読み込み順は OS 環境変数 > .env.local > .env。OS 環境変数は保護され、.env.local の override に対しても保護される。
- .env のパースはコメントやクォート、エスケープに一定の互換性を保つよう実装されていますが、極端に複雑なシェル構文（複数行クォート等）には対応していない可能性があります。
- J-Quants クライアントの retry/backoff ロジックは最大 3 回です。429 レスポンスの Retry-After ヘッダを優先して待機します。
- DuckDB のテーブル定義には多数の CHECK 制約や FOREIGN KEY を含むため、投入データはスキーマに合う形式であることを確認してください。
- strategy / execution / monitoring モジュールは現状でパッケージ雛形のみです。戦略実装やリアルタイム発注フローは今後追加予定です。

互換性（Breaking Changes）
- 初回リリースのため互換性破壊はありません。

今後の予定（短評）
- strategy / execution の実装追加（シグナル生成→発注の一連フロー）
- Slack 通知などの運用監視・アラート機能の拡充
- テストカバレッジと CI/CD パイプラインの整備
- 高可用化／並列実行時のトークン共有・レート制御強化

以上。質問や追記希望があれば教えてください。