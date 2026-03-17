# Changelog

すべての注目すべき変更を記録します。  
このファイルは「Keep a Changelog」形式に従っています。

現在のパッケージバージョン: 0.1.0

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。以下の主要コンポーネントと機能が追加されています。

### Added
- パッケージ基盤
  - パッケージ初期化（kabusys.__init__）とバージョン情報（__version__ = "0.1.0"）。
- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml を基準）。
  - .env と .env.local の優先度制御（OS 環境変数は保護）、自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - .env 行パーサ（export 形式やクォート・エスケープ、インラインコメント等の取り扱い）。
  - Settings クラス：J-Quants / kabuステーション / Slack / DBパス / 実行環境（development/paper_trading/live） / ログレベル等のプロパティとバリデーションを提供。
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーの取得機能を実装（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）。
  - レートリミッタ（120 req/min）実装による固定間隔スロットリング。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）。
  - 401 応答時の自動トークンリフレッシュ（1回のみ）とモジュールレベルのトークンキャッシュ。
  - get_id_token（リフレッシュトークン→IDトークン）実装。
  - DuckDB への冪等保存関数（save_daily_quotes、save_financial_statements、save_market_calendar）：ON CONFLICT を使った更新ロジック、PK 欠損レコードのスキップ、保存件数ログ出力。
  - 型変換ユーティリティ（_to_float、_to_int）による堅牢な入力ハンドリング（空文字列・不正値の None 変換、"1.0" 等の float 文字列の扱い）。
  - レスポンス取得時の JSON デコードエラーハンドリング。
  - fetched_at に UTC タイムスタンプを記録することで Look-ahead Bias のトレースを可能にする設計。
- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を取得して raw_news に保存するフルパイプライン（fetch_rss、save_raw_news、save_news_symbols、run_news_collection）。
  - URL 正規化とトラッキングパラメータ除去（_normalize_url）、正規化URLからの記事ID生成（SHA-256 の先頭32文字）。
  - defusedxml を用いた XML パース（XML Bomb 対策）。
  - SSRF（Server-Side Request Forgery）対策：
    - URL スキーム検証（http/https のみ許可）。
    - ホスト検査でプライベート/ループバック/リンクローカル/マルチキャストアドレスを拒否（DNS 解決および直接 IP 判定）。
    - リダイレクト時にスキームとホストを事前検査するカスタム RedirectHandler を使用。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - テキスト前処理（URL 除去、空白正規化）。
  - 記事挿入はチャンク化してトランザクション内で INSERT ... ON CONFLICT DO NOTHING RETURNING を使用。実際に挿入された ID のみを返す設計。
  - 銘柄コード抽出（4桁数字パターン）と news_symbols テーブルへのバルク保存（重複除去、チャンク挿入、トランザクション管理）。
  - デフォルト RSS ソース（Yahoo Finance カテゴリ等）。
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の多層スキーマ DDL を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
  - 各種制約（NOT NULL, PRIMARY KEY, CHECK）とインデックスを定義。
  - init_schema(db_path) によりディレクトリ作成 → テーブル/インデックス作成を冪等に実行。
  - get_connection(db_path) により既存 DB への接続を提供（初期化は行わない）。
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新・差分取得を想定した ETL ヘルパー（最終取得日取得関数 get_last_price_date/get_last_financial_date/get_last_calendar_date）。
  - ETLResult dataclass により ETL 実行結果（取得件数・保存件数・品質問題・エラー等）を構造化して返却・シリアライズ可能に実装。
  - 市場カレンダーを考慮した営業日調整ヘルパー（_adjust_to_trading_day）。
  - run_prices_etl（差分 ETL 実装の骨格）：最終取得日からのバックフィル（backfill_days デフォルト 3 日）、範囲チェック、fetch→save の呼び出しにより idempotent な更新を行う設計。
- その他
  - 各所でログ出力（info/warning/exception）を行い運用時の観察性を確保。
  - DB 操作はトランザクション内で行い、例外時はロールバックする実装。

### Security
- RSS パーサに defusedxml を採用し、XML インジェクション・XML Bomb を軽減。
- HTTP(S) スキーム以外の URL を許可しないことによりローカルファイルや mailto 等の不正スキームの排除。
- プライベートIP/ループバックアドレスへのアクセス拒否で SSRF リスクを低減。
- レスポンスの最大読み取りバイト数でメモリDoS を防止（Gzip 解凍後もチェック）。

### Notes / Design decisions
- J-Quants API はレート制限（120 req/min）を厳守するため固定間隔（スロットリング）を採用。必要に応じて将来的にトークンバケット等へ変更可能。
- DuckDB への保存は可能な限り冪等（ON CONFLICT）で実装し、元データの再取得・上書きを安全に行えるように設計。
- ETL は Fail-Fast にせず、品質チェックの検出は集約して呼び出し元で対応できるようにする方針。
- テスト容易性のため、id_token 等を外部から注入可能なように設計（ユニットテストでのモックを想定）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

---

今後のリリースでは、以下のような拡張が想定されます（ロードマップ案、参考）:
- ETL の完全実装（prices に続く financials/calendar の run_*_etl ジョブ統合・スケジューリング）。
- quality モジュールの実装と品質チェックルールの追加。
- execution（発注）層の kabu API 統合、約定同期、ポジション管理ロジックの実装。
- 単体テスト・統合テストの追加、および CI/CD 設定。