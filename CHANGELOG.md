# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-17

### Added
- パッケージ初期リリース。パッケージ名: KabuSys（日本株自動売買システム）。
  - src/kabusys/__init__.py にバージョン情報（0.1.0）と公開サブパッケージを定義（data, strategy, execution, monitoring）。
- 環境変数/設定管理モジュール（src/kabusys/config.py）を追加。
  - .env ファイルまたは環境変数から設定を読み込む自動ローダー（プロジェクトルートは .git または pyproject.toml で探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサ（export 形式、クォート内のエスケープ、インラインコメント処理に対応）。
  - 環境変数保護（既存の OS 環境変数を保護して .env.local で上書き可）。
  - Settings クラスを提供（J-Quants、kabuステーション、Slack、DB パス、環境種別とログレベルのバリデーション、is_live/is_paper/is_dev ユーティリティ）。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）を追加。
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得 API を実装。
  - API レート制御（120 req/min）を固定間隔スロットリングで実装（RateLimiter）。
  - 再試行ロジック（最大 3 回、指数バックオフ、HTTP 408/429/5xx の再試行、429 の Retry-After 優先）。
  - 401 受信時はリフレッシュトークンで id_token を自動更新して 1 回リトライ（再帰防止フラグあり）。
  - ページネーション対応（pagination_key を用いた取得ループ）。
  - DuckDB への冪等保存関数を実装（ON CONFLICT DO UPDATE）：save_daily_quotes, save_financial_statements, save_market_calendar。
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を回避できる設計。
  - 型変換ユーティリティ（_to_float, _to_int）を実装（不正な数値は None を返す等の安全処理）。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）を追加。
  - RSS フィードから記事を取得して raw_news に保存する一連の処理を実装。
  - 記事 ID は正規化された URL を SHA-256（先頭32文字）でハッシュ化して生成し冪等性を保証。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去、スキーム/ホスト小文字化）。
  - RSS 受信の堅牢化:
    - defusedxml を使った XML パース（XML Bomb 等への対策）。
    - SSRF 対策（リダイレクト時のスキーム/ホスト検査、ホストがプライベート/IP の場合は拒否）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
    - User-Agent / Accept-Encoding ヘッダの指定。
  - テキスト前処理（URL 除去、空白正規化）。
  - DuckDB へのバルク挿入をトランザクションで実施し、INSERT ... RETURNING を用いて実際に挿入された記事IDを返す（save_raw_news）。
  - 記事と銘柄コードの紐付け処理（extract_stock_codes, save_news_symbols, _save_news_symbols_bulk）。チャンク挿入と ON CONFLICT DO NOTHING による冪等保存。
  - デフォルト RSS ソース（yahoo_finance）を定義。
- DuckDB スキーマ定義と初期化モジュール（src/kabusys/data/schema.py）を追加。
  - Raw / Processed / Feature / Execution 層にまたがるテーブル定義を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 各テーブルの制約（PRIMARY KEY, CHECK, FOREIGN KEY 等）を定義。
  - パフォーマンス向けインデックス群を作成（コード/日付検索・ステータス検索等）。
  - init_schema(db_path) でディレクトリ作成→全 DDL/INDEX 実行→DuckDB 接続を返す。get_connection() で既存 DB に接続。
- ETL パイプライン基盤（src/kabusys/data/pipeline.py）を追加。
  - 差分更新の方針（最終取得日を基に backfill して再取得）を実装。
  - ETLResult dataclass を導入（取得件数・保存件数・品質問題・エラーの集約、シリアライズ用 to_dict）。
  - 市場カレンダーヘルパー（_adjust_to_trading_day）とテーブル最終日取得ユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）を実装。
  - run_prices_etl 等の個別 ETL ジョブを実装開始（差分取得→保存のフロー、jquants_client を利用）。

### Security
- セキュリティ対策を複数導入。
  - RSS パーサに defusedxml を使用して XML 攻撃を防止。
  - RSS フェッチ時に SSRF を防ぐため、リダイレクト先のスキーム検査およびプライベートIP/ループバックの検出を行いアクセスを拒否。
  - .env 管理で OS 環境変数を保護する仕組みを導入（protected set）。
  - HTTP レスポンスのサイズ上限（MAX_RESPONSE_BYTES）でメモリ DoS / Gzip bomb に備える。

### Changed
- （初回リリースのため「変更」はなし）

### Fixed
- （初回リリースのため「修正」はなし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

---

注記:
- strategy/execution/monitoring パッケージの __init__ はプレースホルダとして存在。戦略ロジックや発注モジュールは今後追加予定。
- run_prices_etl などの ETL 関数は差分ロジックを実装しているが、将来的により詳細な品質チェック（quality モジュール）やスケジュール連携が追加される予定。
- 本 CHANGELOG はソースコードから推測して作成しています。実装の詳細・追加・バグ修正は今後のコミットで追記してください。