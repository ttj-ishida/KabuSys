# CHANGELOG

このファイルは Keep a Changelog の形式に従ってこのリポジトリで行われた主要な変更を日本語で記録します。  
フォーマットや意味合いの詳細については https://keepachangelog.com/ja/ を参照してください。

- ルール: すべての変更はセマンティックバージョニングに従います。
- 本ログはコードベースの内容から推測して作成しています。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。主な追加点・設計方針は以下のとおりです。

### Added
- パッケージ基礎
  - パッケージエントリポイントを追加（kabusys.__init__、バージョン: 0.1.0）。
  - モジュール構成: data, strategy, execution, monitoring（__all__に公開）。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数を読み込む自動ローダーを実装。
  - プロジェクトルート検出（.git または pyproject.toml を起点）によりカレントディレクトリに依存しない読み込み。
  - export KEY=val 形式やクォート・コメントのパースに対応する .env パーサを実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 必須環境変数取得ヘルパー（_require）と Settings クラスを提供（J-Quants / kabu / Slack / DB パス / システム環境など）。
  - KABUSYS_ENV と LOG_LEVEL 値検証を実装（許容値チェック）。
  - Path オブジェクトを返す duckdb/sqlite パスプロパティ。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得関数を実装（ページネーション対応）。
  - レート制限（固定間隔スロットリング）を実装して 120 req/min を遵守（内部 RateLimiter）。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）を実装。
  - 401 受信時の自動トークンリフレッシュを1回行って再試行する仕組みを実装（get_id_token とキャッシュ）。
  - JSON デコードエラー時の明示的エラー報告。
  - DuckDB への冪等保存関数を実装:
    - save_daily_quotes: raw_prices への INSERT ... ON CONFLICT DO UPDATE
    - save_financial_statements: raw_financials への INSERT ... ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar への INSERT ... ON CONFLICT DO UPDATE
  - 値変換ユーティリティ（_to_float/_to_int）を実装し、不正値や空文字列を安全に扱う。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集と前処理の実装（DEFAULT_RSS_SOURCES に Yahoo Finance をデフォルト登録）。
  - セキュリティ対策:
    - defusedxml を用いた XML パースで XML Bomb を防御。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストのプライベートアドレス検出、リダイレクト時の事前検証ハンドラ（_SSRFBlockRedirectHandler）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）および gzip 解凍後のサイズ検証。
    - 非 http/https スキームや不正な最終リダイレクトを検出してスキップ。
  - 記事IDは URL 正規化後の SHA-256 ハッシュ先頭32文字で生成（utm_* 等トラッキングパラメータを除去）。
  - テキスト前処理（URL除去、空白正規化）。
  - DuckDB への保存関数:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + INSERT ... RETURNING id を用いて新規挿入IDを返す。チャンク化して1トランザクションで効率的に保存。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols への重複排除したバルク挿入（ON CONFLICT 無視）を実装。
  - 銘柄コード抽出ロジック（4桁数字の候補を抽出し known_codes と照合する extract_stock_codes）。
  - 統合収集ジョブ run_news_collection を実装（ソース単位で独立エラーハンドリング、既存記事はスキップ、紐付け処理を一括で行う）。

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層を意識したテーブル定義を追加（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 各テーブルに適切な制約（PRIMARY KEY、CHECK、FOREIGN KEY）を設定。
  - 頻出クエリ向けのインデックスを定義。
  - init_schema(db_path) によりディレクトリ作成を行い、全DDLとインデックスを実行して初期化するユーティリティを提供。
  - get_connection(db_path) で既存DB接続を返す関数を提供。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新ロジックと ETLResult データクラスを実装（取得数／保存数／品質問題／エラー一覧などを含む）。
  - テーブル存在チェック／最大日付取得ユーティリティ（_table_exists, _get_max_date）。
  - 市場カレンダ補正ヘルパー（_adjust_to_trading_day: 非営業日は直近営業日に調整）。
  - 差分更新用ユーティリティ（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
  - run_prices_etl を実装（差分算出、backfill_days による再取得、jquants_client を用いた取得と保存）。設計上はバックフィルや品質チェック（quality モジュール）と連携する想定。

### Changed
- （初回リリースのため履歴無し）

### Fixed
- （初回リリースのため履歴無し）

### Security
- API/ネットワーク関連に対して複数の安全策を導入:
  - J-Quants クライアントでタイムアウト、リトライ、レート制御、トークン自動更新を実装。
  - RSS 取得で SSRF 対策、gzip 解凍の安全確認、defusedxml による XML 攻撃対策。
  - .env の読み込みでファイル読み取り失敗時に警告を出すなど堅牢性を向上。

---

注記:
- 実装・設計はコードから推測して記載しています。実際のドキュメントやリリースノートと差異がある場合があります。追加の振る舞いや細かい変更点の反映が必要なら、ソースコードやコミットログの追加情報を提供してください。