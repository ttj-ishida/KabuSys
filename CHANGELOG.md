# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) のガイドラインに従って管理しています。

## [0.1.0] - 2026-03-17

### Added
- 初回リリース。日本株自動売買システム「KabuSys」のコア基盤を実装。
- パッケージメタデータ
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - パッケージ公開APIを `__all__ = ["data", "strategy", "execution", "monitoring"]` で宣言。

- 環境設定 / ロード (.env サポート)
  - .env ファイルまたは環境変数から設定を読み込む `kabusys.config` モジュールを追加。
  - プロジェクトルート自動検出 (`.git` または `pyproject.toml` を起点) による .env 自動ロード実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - OS 環境変数を保護するための protected キーセットと上書き制御を実装。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用）。
  - .env パーサは export プレフィックス、クォート文字列、インラインコメント、バックスラッシュエスケープ等に対応。
  - 必須設定取得ヘルパー `_require()` と `Settings` クラスを提供:
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティを用意（例: `jquants_refresh_token`, `kabu_api_password`, `slack_bot_token`, `duckdb_path` 等）。
    - `KABUSYS_ENV` の許容値検証（`development`, `paper_trading`, `live`）および `LOG_LEVEL` の検証。
    - `is_live` / `is_paper` / `is_dev` のユーティリティプロパティを実装。

- データアクセス層 (J-Quants クライアント)
  - `kabusys.data.jquants_client` を追加。
  - API 設計方針:
    - レート制限厳守 (120 req/min) のため固定間隔スロットリング `_RateLimiter` を導入。
    - リトライロジック（指数バックオフ、最大 3 回）、HTTP 408/429 と 5xx をリトライ対象に設定。
    - 401 Unauthorized の場合は ID トークンを自動リフレッシュして 1 回だけリトライする仕組みを実装。
    - ページネーション対応（pagination_key の扱い）。
    - データ取得時点を UTC の `fetched_at` で記録（Look-ahead Bias 防止）。
    - DuckDB への保存は冪等性を担保するため `ON CONFLICT DO UPDATE` を使用。
  - 提供 API:
    - 認証: `get_id_token(refresh_token: str | None) -> str`
    - データ取得: `fetch_daily_quotes`, `fetch_financial_statements`, `fetch_market_calendar`
    - DuckDB 保存: `save_daily_quotes`, `save_financial_statements`, `save_market_calendar`
  - 型変換ユーティリティ `_to_float` / `_to_int` を実装し、空値・不正値を安全に扱う。

- ニュース収集コンポーネント
  - `kabusys.data.news_collector` を追加。
  - RSS フィードからニュース記事を収集して DuckDB (`raw_news`, `news_symbols`) に保存する ETL 機能。
  - 設計上のセキュリティ・堅牢化:
    - defusedxml を使用して XML Bomb 等の攻撃を軽減。
    - SSRF 対策: リダイレクト検査用ハンドラ `_SSRFBlockRedirectHandler`、ホストのプライベートアドレス検査 `_is_private_host`、スキーム検証（http/https のみ許可）。
    - レスポンス最大サイズ制限 (MAX_RESPONSE_BYTES = 10MB) と gzip 解凍後の再チェック。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）とトラッキングパラメータ除去ロジック。
    - 記事IDは正規化URLの SHA-256 ハッシュ先頭32文字で生成し冪等性を確保。
    - URL の検証および許可スキーム以外の除外。
  - DB 周り:
    - `save_raw_news` はチャンク分割（_INSERT_CHUNK_SIZE）してトランザクション内で `INSERT ... ON CONFLICT DO NOTHING RETURNING id` を用い、実際に挿入された新規記事IDのリストを返す。
    - `save_news_symbols` および内部 `_save_news_symbols_bulk` はニュースと銘柄の紐付けをチャンク挿入かつトランザクションで行い、挿入数を正確に返す。
  - テキスト前処理: URL 除去、空白正規化 (`preprocess_text`)。
  - 銘柄コード抽出: 4 桁数字のパターンを検出し、与えられた known_codes に基づいてフィルタリングする `extract_stock_codes` を提供。
  - RSS フェッチ: `fetch_rss(url, source, timeout)` と統合ジョブ `run_news_collection(conn, sources, known_codes, timeout)` を実装。各ソースは独立してエラーハンドリング。

- DuckDB スキーマ定義
  - `kabusys.data.schema` にて DataPlatform に基づくスキーマを提供。
  - 3 層（Raw / Processed / Feature）および Execution 層をカバーするテーブルを定義:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに主キー / チェック制約 / 外部キーを設定し、頻出クエリ用のインデックスも作成。
  - `init_schema(db_path)` によりディレクトリ作成 → 接続 → テーブル/インデックス作成を行い冪等初期化を提供。`get_connection(db_path)` を追加。

- ETL パイプライン基盤
  - `kabusys.data.pipeline` を追加（ETL 管理と差分更新ロジックの基礎）。
  - ETL 結果を表す `ETLResult` dataclass を追加（quality チェック結果、エラー一覧などを含む）。
  - DB の最終取得日取得ユーティリティ: `get_last_price_date`, `get_last_financial_date`, `get_last_calendar_date`。
  - 非営業日調整ヘルパー `_adjust_to_trading_day`（market_calendar を参照して直近営業日に調整）。
  - 差分更新ロジックとバックフィル対応（デフォルト backfill_days = 3）を用いた `run_prices_etl` の実装（取得→保存→ログ）。
  - 最小データ開始日 `_MIN_DATA_DATE`（2017-01-01）と市場カレンダーの先読み設定 `_CALENDAR_LOOKAHEAD_DAYS` を導入。
  - 品質チェック統合のためのフック（quality モジュール参照）を想定した設計。品質チェックは重大度に応じて結果を ETLResult に含める。

- テスト・拡張性を考慮した設計
  - `news_collector._urlopen` をモック差替え可能にしてテストを容易化。
  - jquants_client の id_token 注入パラメータや pipeline の id_token 注入など、テスト容易性を配慮。

### Security
- RSS / XML/HTTP 関連の安全対策を多数導入（defusedxml、SSRF 検査、プライベートIP拒否、レスポンスサイズ制限）。  
- .env 読み込みでは OS 環境変数を保護し、意図しない上書きを防止。

### Notes / Known limitations
- strategy/execution/monitoring パッケージはプレースホルダ（現状空の __init__）であり、戦略実装や発注ロジックはこれから実装予定。
- quality モジュールは参照されているが（pipeline の型など）、この差分に含まれる品質チェックの具体的実装は別途提供が必要。
- 一部の関数（例: run_prices_etl の戻り値の最終組み立て）が途中で切れている可能性があり、ETL の完全なワークフローは今後の追加実装で拡張される予定。

---

今後のリリース予定の例:
- 0.2.0: ETL 完全化（品質チェック実装・スケジューラ連携）、strategy/ execution の初期実装
- 0.3.0: モニタリング・アラート（Slack 通知）と運用用の CLI/サービス化

（以上）