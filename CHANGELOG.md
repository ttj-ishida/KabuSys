# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。

注: このリポジトリは初回リリース相当の内容が含まれています。リリース日はファイル解析時点の日付（2026-03-18）を記載しています。

## [0.1.0] - 2026-03-18

### Added
- 全体
  - パッケージ初期化とバージョン管理を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ構成: data, strategy, execution, monitoring を公開モジュールとして定義。

- 設定 / 環境管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を追加。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索して行う（CWD 非依存）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能（テスト向け）。
  - .env パーサーの実装:
    - コメント、export プレフィックス、シングル/ダブルクォート、エスケープシーケンス、インラインコメント処理などに対応。
  - .env 読み込み時の上書き制御（override, protected）を実装し、OS 環境変数保護に対応。
  - Settings クラスを実装し、アプリケーション設定をプロパティ経由で取得可能に。
    - J-Quants / kabu API / Slack / DB パス（DuckDB/SQLite）など主要設定を取得。
    - KABUSYS_ENV と LOG_LEVEL の値検証（有効値チェック）を導入。
    - is_live / is_paper / is_dev の便利プロパティを提供。
  - settings.jquants_refresh_token 等、必須環境変数未設定時は明確な ValueError を送出。

- J-Quants クライアント（kabusys.data.jquants_client）
  - J-Quants API からのデータ取得と DuckDB への保存のためのクライアント機能を実装。
  - 実装ポイント:
    - レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回）。対象はネットワーク系エラーおよび 408, 429, 5xx。
    - 401 受信時の自動トークンリフレッシュを 1 回行いリトライ（無限再帰回避のため allow_refresh フラグあり）。
    - id_token のモジュールレベルキャッシュを導入しページネーション間で共有。
    - JSON デコードエラー時の明確な例外メッセージ出力。
  - データ取得関数を実装:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務データ、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
    - 取得数ログ出力、ページネーション重複防止（pagination_key の追跡）
  - DuckDB への保存関数を実装（冪等性確保）:
    - save_daily_quotes: raw_prices テーブルへ INSERT ... ON CONFLICT DO UPDATE（fetched_at を記録）
    - save_financial_statements: raw_financials テーブルへ冪等保存
    - save_market_calendar: market_calendar テーブルへ冪等保存、HolidayDivision を解釈して is_trading_day / is_half_day / is_sq_day を決定
  - 型変換ユーティリティ: _to_float, _to_int（文字列→数値変換の堅牢化、空値・不正値に対する None 返却）
  - 設計上の留意点をコメントに明記（Look-ahead Bias 対策として fetched_at を UTC で記録、ON CONFLICT による冪等性など）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news に保存し、銘柄紐付けを行うフル機能を実装。
  - セキュリティ・堅牢性対策:
    - defusedxml を用いた XML パース（XML Bomb 等に対する防御）。
    - SSRF 対策: リダイレクト時のスキーム検証、ホストがプライベートアドレスかどうかの判定（IP/DNS で判定）を行う _SSRFBlockRedirectHandler と _is_private_host。
    - URL スキームは http/https のみ許可。
    - レスポンス最大サイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - Content-Length の事前チェックとオーバーサイズでのスキップ。
  - 収集処理:
    - fetch_rss: RSS を取得して記事リストを返す。名前空間や非標準フィードへフォールバック。
    - preprocess_text: URL 除去、空白正規化。
    - _normalize_url: トラッキングパラメータ（utm_ 等）除去、クエリのソート、フラグメント削除による URL 正規化。
    - _make_article_id: 正規化 URL の SHA-256 先頭 32 文字を記事IDとして採用（冪等性確保）。
    - _parse_rss_datetime: pubDate を UTC naive datetime に変換（失敗時は現在時刻で代替しワーニング）。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いて新規挿入された記事 ID を返す。チャンク処理と 1 トランザクションでの挿入をサポート。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けをチャンク＆トランザクションで保存し、新規挿入数を正確に返す。
  - 銘柄抽出:
    - extract_stock_codes: テキストから 4 桁の銘柄候補を抽出し、既知銘柄セットでフィルタ、重複排除して返す。
  - run_news_collection: 複数 RSS ソースを順次処理し、各ソースごとの新規保存数を返す。既知銘柄が与えられた場合は新規記事に対して銘柄紐付けを一括で実行。ソース単位でのエラーハンドリングにより一部ソース失敗でも他ソースは継続。

- DuckDB スキーマ（kabusys.data.schema）
  - DataPlatform の設計に基づくスキーマ定義と初期化機能を実装:
    - レイヤ: Raw / Processed / Feature / Execution をカバーする多数のテーブルを定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
    - 各テーブルに適切なチェック制約（NOT NULL、CHECK、PRIMARY/FOREIGN KEY）を設定。
    - インデックスを定義して頻出クエリを最適化（銘柄×日付、ステータス検索など）。
  - init_schema(db_path): DB ファイルの親ディレクトリ作成 → DuckDB 接続 → 全 DDL / INDEX を実行 → 接続を返す（冪等）。
  - get_connection(db_path): 既存 DB への接続を返す（スキーマ初期化は行わない旨を注記）。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL 実行結果を表す ETLResult dataclass を導入（取得数、保存数、品質問題、エラーの集約、ヘルパーメソッド）。
  - 差分更新および補助ユーティリティを実装:
    - _table_exists, _get_max_date によるテーブル存在/最大日付チェック。
    - _adjust_to_trading_day: 非営業日の調整（market_calendar が存在する場合に最も近い過去の営業日に調整、最大 30 日遡り）。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date: raw_* テーブルの最終取得日取得。
  - run_prices_etl の実装（差分取得、backfill_days による再取得、J-Quants client の fetch/save 呼び出し）。（ファイル末尾は一部切れているが主要ロジックを含む）

### Security
- ニュース収集で SSRF 緩和: リダイレクト時にスキームと最終ホストを検証し、プライベートアドレスや非 http/https スキームを拒否。
- XML パースに defusedxml を使用して XML による攻撃に対処。
- 外部 API 呼び出しにおけるリトライ制御や RateLimiter によるレート管理を追加し、第三者サービスへの過剰アクセスを防止。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Known issues / 注意事項
- pipeline.run_prices_etl のソースファイル末尾は切れている（この解析対象のコードでは戻り値の一部などが欠けている可能性があります）。実行前に該当関数の完全な実装を確認してください。
- strategy, execution, monitoring パッケージは present だが（__init__.py が存在）、具体的な実装は含まれていない（今後の実装予定）。
- quality モジュールは pipeline 内で参照されているが、この解析対象に quality の実装が含まれていないため、品質チェック機能の統合時に依存関係を満たす必要があります。
- DB スキーマは多くの制約を含むため、既存データ移行時は互換性に注意してください。

---

この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートが存在する場合は、それらを優先して記載・調整してください。