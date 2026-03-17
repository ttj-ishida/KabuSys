# CHANGELOG

すべての変更は Keep a Changelog の慣習に従って記載しています。  
重大な変更点・新機能は「Added」、バグ修正は「Fixed」、セキュリティ関連は「Security」にまとめています。

## [Unreleased]


## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム「KabuSys」のコア機能をまとめて追加。

### Added
- パッケージ構造
  - パッケージのエントリポイントを追加（kabusys.__version__ = 0.1.0、__all__ 指定）。
  - 空のサブパッケージ枠を用意：kabusys.execution, kabusys.strategy, kabusys.data（モジュール分割済み）。

- 環境設定（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行い、配布後の挙動を安定化。
  - .env のパーサ実装（export 形式対応、クォートとエスケープ処理、インラインコメントの取り扱い）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを実装し、各種必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）や DB パスなどをプロパティ経由で取得。KABUSYS_ENV / LOG_LEVEL の値検証を実装（許容値チェック）。
  - settings = Settings() を公開 API として提供。

- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する API クライアントを実装。
  - レート制限保護（固定間隔スロットリング）を実装（デフォルト 120 req/min）。
  - リトライロジック（指数バックオフ、最大 3 回、対象ステータス 408/429/5xx）。
  - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ（トークンキャッシュによりページネーション間で共有）。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT を用いた冪等保存（INSERT ... ON CONFLICT DO UPDATE）により重複更新を回避。
  - JSON デコードエラーや HTTP エラーの詳細ログ出力を実装。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news テーブルへ保存するモジュールを実装。
  - 設計方針に沿った堅牢な前処理：URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除）、記事 ID を正規化 URL の SHA-256 (先頭32文字) で生成。
  - XML パースは defusedxml を利用して XML Bomb 等の攻撃を軽減。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - ホストのプライベートアドレス判定（IP 直接判定 + DNS 解決して A/AAAA レコードを検査）。
    - リダイレクト時にスキームとリダイレクト先のホストを検査するカスタム RedirectHandler を導入。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後のサイズ検証でメモリ DoS を軽減。
  - RSS パース／記事抽出（title, content, pubDate の正規化）、不正な link/guid をスキップする耐障害性。
  - DB 保存はチャンクごとにバルク INSERT を実行し、INSERT ... RETURNING を用いて実際に挿入された新規記事 ID を返す（save_raw_news）。トランザクションでの一括保存を行い、失敗時はロールバック。
  - 記事と銘柄コードの紐付け保存（news_symbols）および一括保存ユーティリティを実装（save_news_symbols, _save_news_symbols_bulk）。
  - 銘柄抽出ユーティリティ（4桁数字パターン + known_codes フィルタ）を提供（extract_stock_codes）。
  - デフォルト RSS ソース（Yahoo Finance）のサンプル定義を追加。

- DuckDB スキーマ（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の4層に対応した DuckDB テーブル DDL を定義。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
  - features, ai_scores 等の Feature テーブル。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブル。
  - 制約（PRIMARY KEY / FOREIGN KEY / CHECK）やインデックスを含む設計。
  - init_schema(db_path) によりディレクトリ作成 → テーブル作成（冪等: CREATE IF NOT EXISTS）→ インデックス作成をまとめて実行して DuckDB 接続を返す。
  - get_connection(db_path) を用意（既存 DB への接続、初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新・バックフィルを意識した ETL ヘルパーを実装。
  - 最終取得日の取得ユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 非営業日の調整ヘルパー（_adjust_to_trading_day）を実装し、市場カレンダーを元に入力日を直近の営業日に合わせる。
  - ETL 実行結果を表す dataclass ETLResult を導入（品質問題リスト・エラー一覧・集計値を含む）。品質チェック結果は辞書化できる to_dict() を提供。
  - run_prices_etl の差分更新ロジック（最終取得日を元に date_from を決定、バックフィル日数の扱い、fetch & save の流れ）を実装（fetch から save までの基本フロー）。

- ロギング
  - 各モジュールで info/warning/exception を用いた詳細ログを実装。リトライやスキップ理由のログ出力を充実。

- テストしやすさ
  - jquants_client や news_collector の外部依存部分は引数でトークン注入や _urlopen の差し替えが可能で、ユニットテストのモックを容易にする設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- RSS XML パーサに defusedxml を採用して XML 関連攻撃を低減。
- RSS フェッチでの SSRF 対策を複数レイヤで実施（スキーム検証、プライベートIP判定、リダイレクト時の再検証）。
- HTTP タイムアウトやレスポンスサイズ上限を設定して、ネットワーク攻撃やメモリ枯渇攻撃の影響を緩和。
- .env 読み込み時に OS 環境変数を保護する protected 機構を導入（override オプションと併用）。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Notes / Migration
- データベース初期化:
  - 初回は schema.init_schema(path) を実行してテーブルを作成してください。その後は get_connection() で接続してください。
- 環境変数:
  - 自動で .env/.env.local を読み込みますが、テスト時など自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants トークン:
  - J-Quants のリフレッシュトークンは環境変数 JQUANTS_REFRESH_TOKEN に設定してください（Settings.jquants_refresh_token を通じて取得）。
- ETL:
  - run_prices_etl 等の ETL 関数は差分取得・バックフィルを前提に設計されています。運用時はバックフィル日数やターゲット日付の運用ルールに注意してください。

もし追加でリリース日やバージョン番号を調整したい、あるいは各モジュールの利用例（簡単なコードスニペット）をCHANGELOGに付けたい場合は教えてください。