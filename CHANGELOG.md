# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

全リリースはセマンティックバージョニングに従います。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買基盤のコア機能群を実装しました。以下はこのリリースで追加された主な機能・設計上のポイントおよびセキュリティ／堅牢化の対策です。

### 追加 (Added)

- パッケージ初期化
  - kabusys パッケージの基本構造を導入（data, strategy, execution, monitoring の公開）。
  - バージョン: 0.1.0

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local からの自動ロード機能を実装（OS環境変数を保護しつつ `.env.local` で上書き可能）。
  - プロジェクトルート探索を .git または pyproject.toml を基準に行うため、実行カレントディレクトリに依存しない設計。
  - .env のパースロジックを実装（export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメント処理）。
  - 自動ロード無効化のための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - Settings クラスを提供し、以下の必須/任意設定をプロパティ経由で取得可能：
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルト値あり）
    - KABUSYS_ENV / LOG_LEVEL の検証機能（有効値チェック）
    - is_live / is_paper / is_dev のヘルパープロパティ

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しの共通処理を実装：
    - 固定間隔スロットリングによるレート制限（120 req/min を守る RateLimiter）。
    - 指数バックオフ付きリトライ（最大 3 回、408/429/5xx を再試行対象）。
    - 401 の場合はリフレッシュトークンで自動的にトークンを更新して 1 回再試行（無限再帰回避）。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）。
    - id_token のモジュールレベルキャッシュ（ページネーション間で共有）。
  - DuckDB への保存関数（冪等性を考慮）：
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - ON CONFLICT DO UPDATE を使ったアップサート、fetched_at を UTC ISOZ で記録
  - 入出力変換ユーティリティ：_to_float, _to_int（堅牢な型変換と不正値ハンドリング）
  - 詳細なログ出力による追跡性の確保

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからの記事収集パイプラインを実装：
    - defusedxml を使った安全な XML パース
    - リダイレクト先とホストの事前検証（SSRF 防止）
    - URL スキームの検証（http/https のみ許可）
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）
    - トラッキングパラメータを削除して URL 正規化、正規化 URL から SHA-256（先頭32文字）で記事 ID 生成（冪等性）
    - コンテンツ前処理（URL除去、空白正規化）
    - DuckDB へのバルク挿入：チャンク挿入、トランザクション、INSERT ... RETURNING を使って実際に挿入されたIDを返す（save_raw_news, save_news_symbols, _save_news_symbols_bulk）
    - 銘柄コード抽出（4桁数字パターンと known_codes フィルタ）
    - run_news_collection によるソース単位の独立したエラーハンドリングと一括処理

- スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - DuckDB 用スキーマを実装（Raw / Processed / Feature / Execution の多層構造）
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw レイヤ
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols など Processed レイヤ
  - features, ai_scores など Feature レイヤ
  - signals, signal_queue, orders, trades, positions, portfolio_performance など Execution レイヤ
  - 運用上の頻出クエリ向けに複数の INDEX を作成
  - init_schema(db_path) によりディレクトリ自動作成→DDL/INDEX 実行の初期化を提供
  - get_connection(db_path) で既存 DB へ接続可能（初回は init_schema を推奨）

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETLResult dataclass により ETL 実行結果を構造化（品質問題やエラー一覧を格納）
  - テーブル存在チェック・最大日付取得のヘルパー（差分取得のため）
  - 市場カレンダーに基づいた営業日補正ヘルパー（_adjust_to_trading_day）
  - 差分更新ロジック（get_last_* を用いた差分算出、backfill_days による再取得、最小取得日 _MIN_DATA_DATE）
  - run_prices_etl 実装（差分取得 → fetch_daily_quotes → save_daily_quotes。バックフィルと未取得判定対応）

### 変更 (Changed)

- 初回リリースのため該当なし。

### 修正 (Fixed)

- 各種パース／型変換の堅牢性改善：
  - .env パースでのクォート内エスケープやインラインコメントの扱いを実装。
  - RSS pubDate のパース失敗時のフォールバック（現在時刻を使用）で raw_news.datetime の NOT NULL 制約に対応。
  - 数値変換（_to_int）で "1.0" のような文字列を適切に扱い、小数部がある場合は None を返すことで誤った切り捨てを防止。

### セキュリティ (Security)

- SSRF 対策（news_collector）：
  - リダイレクト先のスキーム検証、プライベートアドレス拒否、初回ホストのプライベート判定。
- XML インジェクション対策：
  - defusedxml を利用して XML パース（XML Bomb 等を回避）。
- レスポンスサイズ上限と gzip 解凍後のチェック（メモリ DoS / Gzip bomb 対策）。
- 環境変数自動読み込み時に OS の既存環境変数を保護（上書き禁止リスト）。

### 既知の制限 / 注意点 (Notes)

- 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。未設定時は Settings プロパティ経由で ValueError が発生します。
- デフォルトの DuckDB / SQLite パスは settings で定義されています（必要に応じて環境変数で上書きしてください）。
- init_schema はスキーマ作成のみを行います。既存データのマイグレーション処理は本リリースでは含まれていません。
- jquants_client のリトライ／レート制御は基本的な設計を含みますが、実運用ではモニタリングやメトリクス向けの追加実装を推奨します。
- pipeline.run_prices_etl は本リリースで差分取得の主処理をサポートしますが、財務データ・カレンダーの ETL 統合や品質チェックモジュール（quality）の呼び出し連携は別途実装が必要です（quality モジュール想定の設計を含む）。

---

（この CHANGELOG はリポジトリ内のコード実装からの推測に基づいて作成しています。追加の変更履歴や日付修正がある場合は適宜更新してください。）