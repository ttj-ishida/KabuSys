CHANGELOG
=========

すべての重要な変更点をここに記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

[0.1.0] - 2026-03-18
--------------------

初回リリース: KabuSys — 日本株自動売買システムの基礎機能を実装しました。

Added
- パッケージ初期化
  - パッケージバージョンを src/kabusys/__init__.py にて "0.1.0" として定義。
  - パッケージ公開 API: data, strategy, execution, monitoring。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート自動検出: .git または pyproject.toml を基準に探索（CWD に依存しない）。
  - 自動 .env ロード: OS 環境変数 > .env.local > .env の優先順位で読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
  - .env パーサ実装: export 形式、クォート処理、インラインコメント扱い、空行/コメント行スキップ等に対応。
  - 必須環境変数チェック (_require) を追加（未設定時は ValueError）。
  - Settings のプロパティ化: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH 等。
  - 環境 (KABUSYS_ENV) とログレベル (LOG_LEVEL) の値検証（許可値の制約）。
  - is_live / is_paper / is_dev のユーティリティプロパティ。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - レート制限実装: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter。
  - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx をリトライ対象。
  - 401 (Unauthorized) 受信時はリフレッシュトークンで id_token を自動リフレッシュして 1 回だけリトライ。
  - id_token のモジュールレベルキャッシュを導入（ページネーションで共有）。
  - JSON デコードエラーや HTTP エラーを適切に扱い、ログ出力。
  - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装（冪等: ON CONFLICT DO UPDATE）。
  - 値変換ユーティリティ (_to_float, _to_int) を実装し不正値を安全に扱う。
  - 取得時刻 (fetched_at) を UTC で記録し Look-ahead bias のトレーサビリティを保持。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news に保存する fetch_rss / save_raw_news 等を実装。
  - セキュリティ対策:
    - defusedxml を使用した XML パースで XML Bomb 等の攻撃を緩和。
    - URL スキーム検証 (http/https のみ許可)。
    - SSRF 防止: リダイレクト先のスキーム・ホストを検査するカスタム RedirectHandler とホストのプライベートアドレス判定。
    - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10MB) を導入しメモリ DoS を防止。gzip 解凍後も検査。
  - 記事ID は URL 正規化後の SHA-256 ハッシュの先頭 32 文字で生成し冪等性を保証（トラッキングパラメータ除去、クエリソート、フラグメント削除）。
  - テキスト前処理 (URL 除去、空白正規化) を実装。
  - DB 保存はチャンク化 (_INSERT_CHUNK_SIZE=1000) しトランザクションでまとめて実行、INSERT ... RETURNING を使って実際に挿入された件数を正確に返却。
  - 銘柄抽出ロジック extract_stock_codes を実装（4桁数字パターン、known_codes フィルタ）。
  - run_news_collection: 複数ソース独立処理、失敗ソースのスキップ、記事保存後に銘柄紐付けを一括保存。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく多層スキーマを実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型制約・チェック制約・主キー・外部キーを付与。
  - 頻出クエリ向けのインデックスを定義（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) でディレクトリ作成→テーブル作成→インデックス作成までを実行する初期化関数を提供。get_connection() で接続取得のみ可能。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新を行う ETL の骨組みを実装:
    - 最終取得日からの差分取得、バックフィル (backfill_days=3 がデフォルト) による後出し修正吸収。
    - 市場カレンダーの先読み (_CALENDAR_LOOKAHEAD_DAYS = 90)。
    - ETLResult データクラス: 取得件数・保存件数・品質問題リスト・エラーの一覧を保持。has_errors / has_quality_errors 等のユーティリティを提供。
    - テーブル存在確認と最大日付取得ユーティリティ (_table_exists, _get_max_date)。
    - 非営業日調整ヘルパー (_adjust_to_trading_day)。
    - 個別 ETL ジョブの起点として run_prices_etl（差分取得→保存）を実装（J-Quants クライアントを用いる）。
  - テスト容易性を考慮し、id_token 等の注入ポイントを用意。

- その他
  - モジュール設計上、テストの差し替えが容易になるように _urlopen 等をラップ（モック置換可能）。

Security
- RSS 処理で defusedxml を採用し XML 関連の攻撃リスクを低減。
- ニュース取得で SSRF 対策を実装（スキーム検証・プライベートホスト拒否・リダイレクト時検査）。
- .env 読み込み時に OS 環境変数を保護する protected セットを使用（.env.local の override 時に保護可能）。

Notes / Implementation details
- API のレート制御は固定間隔スロットリングで実装。厳密なトラフィックピーク対応が必要な場合は将来的にトークンバケット等を検討してください。
- jquants_client のリトライは最大 3 回。429 の場合は Retry-After ヘッダを優先して待機。
- DuckDB への保存は原則冪等（ON CONFLICT DO UPDATE / DO NOTHING）で設計。
- ニュース記事の ID は URL の正規化に依存するため、ソース側の URL フォーマット変更により重複判定に影響が出る可能性があります。
- pipeline.run_prices_etl 等は差分ロジックに依存するため、マニュアルでの full-backfill を行う場合は date_from を明示的に指定してください。
- 一部のモジュール（quality 等）は参照されているが、このリリースでは品質検査ロジックの詳細実装は外部モジュールに依存しています（quality.QualityIssue を想定）。

今後の予定（例）
- quality モジュールの具体的チェック実装と ETL での自動対応ポリシー。
- strategy / execution / monitoring の具象実装（現在はパッケージ名のみ）。
- API レート上限に合わせた並列化とスループット最適化。
- ユニットテスト・統合テストおよび CI の整備。

-- End of CHANGELOG --