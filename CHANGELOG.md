# Changelog

すべての注目すべき変更を記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。  
安定版リリースのみをここに記載します。

## [Unreleased]

(なし)

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買プラットフォームの基盤機能を実装しました。

### Added
- パッケージ基盤
  - kabusys パッケージの初期化（バージョン: 0.1.0）。
  - サブパッケージプレースホルダ: data, strategy, execution, monitoring をエクスポート。

- 設定管理（kabusys.config）
  - .env / .env.local または環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）によりカレントディレクトリ非依存で自動読み込み。
  - .env のパース機能強化（export 構文、クォート内エスケープ、インラインコメント考慮）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス / 環境種別 / ログレベル等のプロパティを取得（必須キーは未設定時に ValueError を送出）。
  - 環境値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- J-Quants データクライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制御（固定間隔スロットリング、デフォルト120 req/min）。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）。429 時は Retry-After を尊重。
  - 401 受信時にリフレッシュトークンによる id_token 自動リフレッシュを1回行う仕組み（無限再帰防止）。
  - id_token のモジュールレベルキャッシュでページネーション間の共有を実現。
  - API 取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（マーケットカレンダー）
  - DuckDB への保存関数（冪等性を重視、ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ取り込み時に fetched_at を UTC で記録（Look-ahead bias 対策）。
  - 型変換ユーティリティ (_to_float / _to_int) を実装し不正値を安全に扱う。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからのニュース収集モジュールを実装（デフォルトソース: Yahoo Finance）。
  - URL 正規化とトラッキングパラメータ除去、SHA-256（先頭32文字）による記事ID生成で冪等性を確保。
  - XML パースに defusedxml を採用して XML Bomb 等の攻撃を軽減。
  - SSRF 対策:
    - リダイレクト先のスキームとホストを検査するカスタムリダイレクトハンドラを実装。
    - 事前にホストがプライベートアドレスかを検査し内部ネットワークアクセスを拒否。
    - http/https 以外のスキームを拒否。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後サイズ検査でメモリDoS対策。
  - RSS 取得関数 fetch_rss（エラーハンドリング・前処理含む）を実装。
  - DB 保存機能（DuckDB 使用）:
    - save_raw_news: INSERT ... RETURNING を用いて実際に挿入された記事IDリストを返す。チャンク化 & トランザクションで処理。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを INSERT ... RETURNING で正確にカウント。
  - テキスト前処理（URL除去・空白正規化）と銘柄コード抽出ロジック（4桁数字パターン、既知銘柄セット照合）。

- スキーマ管理（kabusys.data.schema）
  - DuckDB 用スキーマ定義と初期化機能を実装。
  - 3層構造（Raw / Processed / Feature）および Execution レイヤーのテーブル DDL を定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 頻出クエリ向けのインデックスを定義。
  - init_schema(db_path) でディレクトリ作成・DDL実行・インデックス作成を行い接続を返す。get_connection() で既存 DB へ接続。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新を行う ETL パイプラインの基盤を実装。
  - ETLResult データクラス（取得数／保存数／品質問題／エラーの集計とシリアライズ機能）を提供。
  - テーブル存在確認・最大日付取得ユーティリティ（_table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 市場カレンダーに基づく営業日調整ヘルパー（_adjust_to_trading_day）。
  - run_prices_etl 実装の骨子（差分算出 / backfill_days を使った再取得 / jquants_client 経由の取得と保存）。（差分更新・バックフィル設計に対応）

### Security
- RSS パーサに defusedxml を採用し XML による攻撃を緩和。
- ニュース取得時の SSRF 対策（リダイレクト検査、プライベートIP検出、許可スキーム制限）。
- HTTP 応答の読み取り上限と gzip 解凍後のサイズ検査でメモリ爆発攻撃を防止。

### Notes
- 各モジュールのログ出力を適切に行うよう設計されており、運用時の監査・デバッグに役立ちます。
- 初期リリースのため、運用前に環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）の設定が必須です。
- ETL パイプラインや実行系（strategy / execution / monitoring）は基盤を含む実装が揃っていますが、運用ポリシー・追加の検証・統合テストが推奨されます。

---

生成元: ソースコードより推測して作成。