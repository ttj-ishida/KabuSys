# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の記法に従っています。  
セマンティックバージョニングを使用します。

## [Unreleased]

### Added
- 初期ライブラリ骨格を追加
  - パッケージメタ情報: kabusys/__init__.py にバージョン情報と主要サブパッケージを定義 (data, strategy, execution, monitoring)。
- 環境設定/ロード機能を実装 (src/kabusys/config.py)
  - .env / .env.local ファイルおよび OS 環境変数からの自動読み込み機能を追加（読み込み優先度: OS > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を探索して行う（CWD 非依存）。
  - .env の行パースで export プレフィックス、シングル/ダブルクォートおよびバックスラッシュによるエスケープ、インラインコメントの扱いに対応。
  - 環境変数上書きの際に OS 環境変数を保護する protected 機能を実装。
  - Settings クラスを導入し、J-Quants / kabu / Slack / DB パス等の設定プロパティを提供。KABUSYS_ENV と LOG_LEVEL の値検証および is_live / is_paper / is_dev のヘルパープロパティを実装。

- J-Quants API クライアントを実装 (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、市場カレンダーを取得する fetch_* API を実装（ページネーション対応）。
  - API レート制限を守る固定間隔スロットリング（120 req/min）を実装する RateLimiter を導入。
  - 再試行ポリシー（指数バックオフ、最大3回）を実装。再試行対象に 408/429/5xx を含む。429 の場合は Retry-After ヘッダを尊重。
  - 401 レスポンス受信時はリフレッシュトークン経由で id_token を自動リフレッシュして 1 回だけ再試行する仕組みを実装（無限再帰防止の allow_refresh フラグあり）。
  - get_id_token() により refresh_token から idToken を取得。
  - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装。ON CONFLICT DO UPDATE による冪等保存を実現。
  - データ変換ユーティリティ (_to_float, _to_int) を実装し、型安全な変換を行う。

- ニュース収集モジュールを実装 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を取得し raw_news に保存する fetch_rss / save_raw_news / run_news_collection を実装。
  - セキュリティ対策:
    - defusedxml を利用して XML 関連の攻撃を防止。
    - SSRF 対策としてリダイレクト先のスキーム検証とプライベートアドレス検出を行うカスタムリダイレクトハンドラを実装。
    - URL スキームは http/https のみ許可。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入し、読み込み上限を超えた場合にはスキップ（Gzip展開後も検査）。
    - gzip 圧縮の解凍に失敗した場合は安全にスキップ。
  - 冪等性と一貫性:
    - 記事IDは URL 正規化（トラッキングパラメータ除去・クエリソート等）後に SHA-256 の先頭32文字で生成し、ON CONFLICT により重複挿入を防止。
    - INSERT ... RETURNING を用いて実際に新規挿入された記事IDのリストを取得。
    - 銘柄紐付け news_symbols についてチャンク化して一括保存（ON CONFLICT DO NOTHING、トランザクション管理）。
  - テキスト前処理（URL 除去・空白正規化）と記事公開日時の RFC2822 パース（タイムゾーンを UTC に正規化）を実装。
  - 記事本文から 4 桁銘柄コード抽出（既知銘柄セットフィルタ）を実装。

- DuckDB スキーマ定義と初期化機能を実装 (src/kabusys/data/schema.py)
  - DataSchema に基づく多層テーブル群を定義（Raw / Processed / Feature / Execution 層）。
  - raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等の DDL を提供。
  - 頻出クエリを想定したインデックス群を定義。
  - init_schema(db_path) により DuckDB ファイルの親ディレクトリ自動作成後、全テーブルとインデックスを冪等に作成して接続を返す。
  - get_connection(db_path) で既存 DB へ接続するユーティリティを提供。

- ETL パイプライン基盤を実装 (src/kabusys/data/pipeline.py)
  - 差分更新ロジック（最終取得日からの差分取得、backfill による数日前からの再取得）を実装。
  - ETLResult dataclass を導入し、取得件数、保存件数、品質チェック結果、エラー一覧等を構造化して返却可能に。
  - 市場カレンダー先読み日数（_CALENDAR_LOOKAHEAD_DAYS = 90）やデフォルトバックフィル日数（3日）等を定義。
  - DB の最終取得日取得ユーティリティ（get_last_price_date 等）を実装。
  - run_prices_etl() に差分取得・保存の流れを実装（date_from 自動算出、_MIN_DATA_DATE を考慮）。

### Security
- ニュース収集における SSRF 対策、XML パーサの安全化、受信バイト上限の導入により外部入力に対する堅牢性を強化。
- .env 読み込み時に OS 環境変数を保護する仕組みを実装（意図しない上書きを防止）。

## [0.1.0] - 2026-03-17

初期リリース相当の機能群を確定（上記 Added / Security のスナップショット）。  
- 上記の主要機能をパッケージ化して v0.1.0 としてリリース。
- ドキュメントや設計ノートをソース内コメントとして同梱（API レート制限方針、リトライ仕様、冪等性・トレーサビリティ設計など）。

### Known issues / TODO
- pipeline.run_prices_etl の戻り値や一部の ETL 完了処理については拡張・統合テストが必要（コード内に処理継続や結果集約のための拡張ポイントあり）。
- strategy / execution / monitoring サブパッケージは初期 stubs が存在するが、戦略ロジック・発注統合・監視ワークフローは今後実装予定。
- 品質チェックモジュール (quality) は参照されているが、本リリースでの実装状況に応じて挙動確認が必要（ETLResult と連携するチェックの追加予定）。

---

以上。リリースノートはコードから推測して作成しています。実際の変更履歴やリリース日付を確定する際は、コミット履歴やプロジェクトポリシーに合わせて調整してください。