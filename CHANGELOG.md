# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

現在日付: 2026-03-17

## [Unreleased]
- 今後のリリースに向けた予定・メモ:
  - テストカバレッジ（特にネットワーク/SSRF・XMLパース・DuckDB トランザクション周り）の強化
  - execution, strategy, monitoring パッケージの実装拡充（現状はパッケージプレースホルダ）
  - pipeline の ETL ジョブ追加（財務データ・カレンダー用の差分ETL、品質チェックの自動アクション）
  - エラーレポートを Slack に通知する監視機能実装
  - パフォーマンス計測・メトリクス出力の追加

---

## [0.1.0] - 2026-03-17
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン "0.1.0" を設定（src/kabusys/__init__.py）。
  - パッケージ公開 API のプレースホルダモジュール: data, strategy, execution, monitoring（各 __init__）。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出（CWD 非依存）。
  - .env 自動読み込みの優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パースの強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のエスケープ処理
    - インラインコメント処理（クォート有無での挙動差分）
  - 必須設定取得用ヘルパー _require() と Settings クラスを提供。
  - 主要設定プロパティを用意（J-Quants トークン、kabu API 設定、Slack 設定、DB パス、環境種別/ログレベル判定ヘルパーなど）。
  - KABUSYS_ENV / LOG_LEVEL の検証ロジック実装（不正値は例外）。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 基本設計:
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx をリトライ対象）。
    - 401 時の自動トークンリフレッシュ（1 回のみ）と再試行。
    - ページネーション対応（pagination_key を使った取得ループ）。
    - データ取得時に fetched_at を UTC で記録（Look-ahead Bias 対策）。
    - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で重複を排除。
  - 提供関数:
    - get_id_token(refresh_token=None): リフレッシュトークンから id_token を取得（/token/auth_refresh）。
    - fetch_daily_quotes(...): 日足データ取得（ページネーション）。
    - fetch_financial_statements(...): 財務（四半期）データ取得（ページネーション）。
    - fetch_market_calendar(...): JPX マーケットカレンダー取得。
    - save_daily_quotes(conn, records): raw_prices へ冪等保存（fetched_at に UTC ISO8601 を格納）。
    - save_financial_statements(conn, records): raw_financials へ冪等保存。
    - save_market_calendar(conn, records): market_calendar へ冪等保存（取引日/半日/SQ 日フラグ化）。
  - ユーティリティ: 型安全な _to_float / _to_int 関数（空文字や不正値を None に変換）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからの記事収集と DuckDB への保存機能を実装。
  - セキュリティ・堅牢性設計:
    - defusedxml を用いた XML パース（XML Bomb 等対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホスト/リダイレクト先のプライベートアドレス検出によるブロック、リダイレクト時の事前検査ハンドラ実装。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後の再検査（Gzip bomb 対策）。
    - 許可されないスキームやプライベートホストへのアクセスは拒否・ログ出力。
  - 機能:
    - URL 正規化 (utm_* 等のトラッキングパラメータ除去、クエリソート、フラグメント削除)。
    - 記事ID は正規化 URL の SHA-256 先頭32文字で生成し冪等性を担保。
    - テキスト前処理（URL除去、空白正規化）。
    - fetch_rss(url, source, timeout): RSS 取得・パース・記事リスト生成。RSS の content:encoded 優先、pubDate を UTC naive datetime に正規化。
    - save_raw_news(conn, articles): raw_news にチャンク単位で INSERT ... RETURNING を使って挿入（トランザクション、ON CONFLICT DO NOTHING、挿入された ID を返す）。
    - save_news_symbols(conn, news_id, codes) / _save_news_symbols_bulk(conn, pairs): news_symbols への紐付け保存（INSERT ... RETURNING、トランザクション）。
    - extract_stock_codes(text, known_codes): テキストから 4 桁の銘柄コードを抽出（重複除去、known_codes フィルタ）。
    - run_news_collection(conn, sources=None, known_codes=None, timeout=30): ソース毎に独立して取得→保存→銘柄紐付けを実行。各ソースは個別にエラーハンドリングして継続。

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく多層スキーマを定義（Raw / Processed / Feature / Execution 層）。
  - Raw 層: raw_prices, raw_financials, raw_news, raw_executions。
  - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols。
  - Feature 層: features, ai_scores。
  - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance。
  - 各テーブルに適切な型・CHECK 制約・PRIMARY KEY を設定（データ整合性を重視）。
  - よく使うクエリ向けにインデックスを作成（code×date、status、signal_id 等）。
  - init_schema(db_path): ディレクトリ自動作成（必要時）、DDL を順序を考慮して実行しテーブルを初期化（冪等）。
  - get_connection(db_path): 既存DBへの接続を返すヘルパー。

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETL 処理の設計とヘルパー関数群を実装。
  - ETLResult dataclass を追加（target_date、取得数/保存数、品質問題、エラー要約などを格納）。
  - テーブル存在チェック・最大日付取得ユーティリティ (_table_exists / _get_max_date)。
  - 取引日調整ヘルパー (_adjust_to_trading_day) を実装（市場カレンダーを利用して非営業日を直近営業日に調整）。
  - 差分更新用ヘルパー: get_last_price_date / get_last_financial_date / get_last_calendar_date。
  - run_prices_etl(...): 株価差分 ETL の骨格実装（差分の自動算出、backfill_days による再取得、jquants_client の fetch/save を呼び出す）。（注: ファイル末尾でコードが断片化しているが、差分ETL の主要ロジックを実装済み）

### Security
- ニュース収集: defusedxml、SSRF 検査、レスポンスサイズ上限、gzip 解凍後検査を導入して外部入力由来の攻撃リスクを低減。
- .env の読み込みは OS 環境変数を保護する仕組み（protected set）を導入。

### Notes / Migration
- 初回利用時は init_schema() を使って DuckDB スキーマを初期化してください。既存 DB に対しては冪等でスキーマを作成します。
- 環境変数未設定で必須項目（例: JQUANTS_REFRESH_TOKEN / SLACK_BOT_TOKEN 等）を参照すると ValueError が発生します。.env.example を参考に .env を用意してください。
- .env の自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途想定）。

### Known limitations
- strategy, execution, monitoring パッケージはプレースホルダのまま（実装未完）。
- pipeline モジュールには品質チェック呼び出しの骨格と ETLResult があるが、quality モジュールの詳細実装や ETL のすべてのジョブ（財務・カレンダーの差分ETL 呼び出し等）が本リリースにおいて完全ではない可能性があります。
- ネットワーク関連のエラー・タイムアウト処理は実装済みだが、実稼働での負荷・スロットリング調整は運用でチューニングが必要です。

---

以上。