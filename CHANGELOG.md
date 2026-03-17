# Changelog

すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。

フォーマットの意味:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティに関する変更

## [0.1.0] - 2026-03-17

初回リリース — 日本株自動売買システム「KabuSys」のコア機能を実装しました。

### Added
- パッケージ基盤
  - パッケージ情報を定義（src/kabusys/__init__.py）。エクスポート対象モジュール: data, strategy, execution, monitoring。バージョンは 0.1.0 に設定。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env 読み込み機能（プロジェクトルートの判定は .git または pyproject.toml を使用）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env 行パーサは `export KEY=val` 形式、引用符付き値、インラインコメント（適切なケースのみ）に対応。
  - 必須環境変数取得の `_require`、各種設定プロパティ（J-Quants、kabuステーション、Slack、DB パス、環境モード・ログレベル判定）を実装。env/log_level の妥当性チェックを行う。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日次株価（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得機能を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - API 呼び出し共通実装 `_request` を導入。機能:
    - 固定間隔のレートリミッタ（120 req/min）を実装し間隔制御。
    - リトライロジック（指数バックオフ、最大 3 回、対象 HTTP ステータス: 408, 429, 5xx）。429 の場合は Retry-After を優先。
    - 401 受信時はリフレッシュトークンを用いたトークン再取得を 1 回だけ行い再試行（無限再帰を防止）。
    - JSON デコード失敗時の明示的なエラー。
    - ページネーション対応（pagination_key を用いた繰り返し取得）。
  - get_id_token による ID トークン取得（refresh token を settings から利用可能）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）:
    - fetched_at を UTC ISO 形式で記録し、Look-ahead Bias を防止。
    - INSERT ... ON CONFLICT DO UPDATE により冪等性を確保。
    - 入力値変換ユーティリティ（_to_float, _to_int）を提供。_to_int は "1.0" のような浮動小数文字列を扱い、小数部が非ゼロなら None を返す等の安全な振る舞い。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからニュース記事を収集し raw_news へ保存する機能を実装（fetch_rss, save_raw_news, save_news_symbols, _save_news_symbols_bulk, run_news_collection）。
  - セキュリティ・堅牢性対策:
    - defusedxml を使用して XML Bomb 等に対応。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストがプライベート/ループバック/リンクローカルでないことのチェック、リダイレクト先の事前検証用ハンドラ `_SSRFBlockRedirectHandler` を導入。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - User-Agent と Accept-Encoding の指定、Content-Length の事前チェック。
  - 安全性・品質向上のための前処理:
    - URL 正規化（トラッキングパラメータ除去、キーソート、フラグメント除去）および記事 ID を SHA-256（先頭32文字）で生成して冪等性を保証。
    - テキスト前処理（URL 除去、空白正規化）。
    - pubDate のパース（タイムゾーンを UTC に正規化、パース失敗時には代替時刻と警告）。
  - DB 保存はチャンク化してトランザクション内で実施し、INSERT ... RETURNING を利用して新規挿入されたレコードのみを返す実装。
  - 銘柄コード抽出（正規表現で 4 桁数字を抽出し、known_codes に基づきフィルタ）を提供。
  - デフォルト RSS ソースとして Yahoo Finance のビジネスカテゴリ (news.yahoo.co.jp) を設定。

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層をカバーするテーブル定義を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 各テーブルに適切な制約（PRIMARY KEY, CHECK 等）を付与。
  - 検索性能を考慮したインデックス群を定義。
  - init_schema(db_path) によりファイルの親ディレクトリ自動作成・DDL 実行・インデックス作成を行い、冪等に初期化可能。
  - get_connection(db_path) で既存 DB に接続可能（スキーマ初期化はしない）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETL 実行結果を表す ETLResult dataclass を追加（品質問題リスト、エラーリスト、ヘルパープロパティ等を含む）。
  - 差分取得を支援するユーティリティ（テーブル存在チェック、最大日付取得）を実装。
  - 市場カレンダーを参照して非営業日を直近営業日に調整する _adjust_to_trading_day を実装。
  - 差分更新方針（最終取得日からの backfill_days による再取得）を導入。
  - run_prices_etl の実装（差分算出、fetch_daily_quotes を用いた取得、save_daily_quotes による保存）。（注: ファイル末尾で一部コードが切れていますが、差分ロードの設計は実装済み）

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector にて複数の SSRF / XML / DoS 対策を導入:
  - defusedxml の利用、リダイレクト先スキームとホスト検査、プライベート IP 判定、レスポンスサイズ制限、gzip 解凍後のサイズ検査。
- .env 読み込み時に OS 環境変数を保護する protected 機構を導入（.env.local による上書きを許可するが OS 環境変数は上書きされない）。

### Notes / Known limitations
- jquants_client の _request は urllib を使用しており、細かい HTTP ヘッダ制御やセッション管理が不要な用途を想定しています。必要に応じて requests 等への切り替え検討が可能です。
- run_prices_etl の続きを含めた ETL の統合ロジック（全 job 実行、品質チェックの統合処理など）は今後の拡張対象。
- NEWS の記事 ID は URL ベースに依存するため、配信元の URL 仕様変更は抽出結果に影響を与える可能性があります。

------------------------------------------------------------
今後のリリースでは、strategy / execution / monitoring 層の実装、ETL のスケジューリング、テストカバレッジ強化、ならびに運用向けの observability（メトリクス、アラート）を追加予定です。