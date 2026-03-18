Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠です。

[0.1.0] - 2026-03-18
-------------------

初期リリース。日本株自動売買システム「KabuSys」のコアライブラリを実装しました。以下はコードベースから推測してまとめた主要な追加点・設計方針・注意点です。

Added
- パッケージ基盤
  - パッケージのトップレベル: kabusys（__version__ = "0.1.0"）
  - エクスポートモジュール: data, strategy, execution, monitoring（各サブパッケージの枠組みを用意）

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から読み込む自動ロード機能を実装
    - 自動ロードの優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD に依存しない）
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサ: export 形式 / クォート / コメント処理に対応
  - Settings クラスを提供（プロパティ経由で取得）
    - 必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError）
    - 任意/デフォルト: KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DB パス設定: DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - 環境種別とログレベルの検証: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパー: is_live, is_paper, is_dev

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 取得可能データ:
    - 株価日足（OHLCV）
    - 財務データ（四半期 BS/PL）
    - JPX マーケットカレンダー
  - 設計上の特徴:
    - レート制限遵守: 固定間隔スロットリングで 120 req/min（_RateLimiter）
    - リトライロジック: 指数バックオフ（base=2.0）、最大 3 回、対象ステータス: 408/429/5xx およびネットワークエラー
    - 401 時の自動トークンリフレッシュを1回だけ行う（無限再帰対策あり）
    - ページネーション対応（pagination_key を利用）
    - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を回避
    - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で重複を排除
  - 公開API:
    - get_id_token(refresh_token: Optional[str]) -> str
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページング対応）
    - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB 保存、更新もサポート）
  - 型変換ユーティリティ: _to_float, _to_int（不正値は None を返す）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集して raw_news に保存する機能
  - セキュリティ対策と堅牢化:
    - defusedxml を使用し XML Bomb 等の攻撃を防御
    - SSRF 対策: URL スキーム検証（http/https 限定）、ホストがプライベート/ループバック/リンクローカルであれば拒否（DNS 解決して A/AAAA を確認）
    - リダイレクト時も検査する専用の RedirectHandler を用意
    - 受信サイズ上限: MAX_RESPONSE_BYTES = 10MB（Content-Length と実際の読み取りでチェック、gzip 解凍後も検査）
  - 正規化・冪等性:
    - URL 正規化: トラッキングパラメータ（utm_* 等）を除去し、スキーム/ホスト小文字化・フラグメント削除・クエリソート
    - 記事 ID: 正規化 URL の SHA-256 の先頭32文字を利用（冪等性保護）
    - テキスト前処理: URL 除去、空白正規化
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING と INSERT ... RETURNING id を使い、新規挿入された記事ID一覧を返す（チャンク挿入、トランザクション）
    - save_news_symbols / _save_news_symbols_bulk: news_symbols への紐付けをバルク挿入（ON CONFLICT DO NOTHING, RETURNING カウント）
  - 銘柄抽出: テキストから 4 桁数字を抽出し known_codes に基づいてフィルタ（重複除去）
  - run_news_collection: 複数 RSS ソースを順次収集し、エラーがあっても他ソースを継続。既知銘柄との紐付け処理を実行

- DuckDB スキーマ定義（kabusys.data.schema）
  - init_schema(db_path) で以下を含むテーブルを作成（DataSchema.md 想定設計に沿う）
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（CHECK, PRIMARY KEY, FOREIGN KEY）と推奨インデックスを定義
  - get_connection(db_path): 既存 DB へ接続（初回は init_schema を推奨）

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult dataclass を導入（target_date, fetched/saved カウント、quality_issues, errors 等）
    - has_errors / has_quality_errors / to_dict ヘルパーを実装
  - 差分更新設計:
    - デフォルトバックフィル: backfill_days = 3（最終取得日の数日前から再取得し後出し修正を吸収）
    - 最小データ開始日: 2017-01-01（初回ロード時）
    - 市場カレンダー先読み日数: 90 日
  - テーブル存在チェック・最終取得日取得ユーティリティを追加
  - run_prices_etl の骨格（date_from 自動算出、fetch→save の流れ）を実装

Security
- ニュース収集における SSRF 防御、defusedxml 導入、レスポンスサイズ制限など、多層的な防御を実装
- J-Quants クライアントではトークン取り扱いに注意（トークンの自動リフレッシュあり）

Performance / Reliability
- API 呼び出しに対して固定間隔スロットリングと指数バックオフを組み合わせて安定性を確保
- DuckDB への書き込みはバルク/トランザクション化し、重複対策（ON CONFLICT）によって冪等性を担保
- RSS 保存もチャンク化・INSERT RETURNING を用いて実際に追加された件数を正確に把握

Notes / Migration / 使用上の注意
- 必須環境変数（本番利用前に設定必須）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- データベース初期化:
  - init_schema(settings.duckdb_path) を呼んでスキーマを作成してください（":memory:" でインメモリ DB 可能）
- 自動 .env ロードはデフォルトで有効。テストなどで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- KABUSYS_ENV と LOG_LEVEL は受け入れ可能な値を検証します。値が不正だと起動時に ValueError が発生します。
- ニュース収集の既知銘柄抽出は known_codes を与えることで有効化される（与えない場合は紐付け処理をスキップ）

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Acknowledgements / References
- 実装における設計ノート（コード中のコメントより推測）
  - RateLimiter、トークンのページネーション間キャッシュ、Look-ahead Bias 対策（fetched_at）、ETL の差分更新と品質チェックの考え方等が明記されています。

（補足）この CHANGELOG は与えられたソースコードを基に実装意図・機能を推測して作成しています。実際のリリースノートとして用いる場合は、リリース日時・責任者・リリース手順・テストカバレッジなどの追記を推奨します。