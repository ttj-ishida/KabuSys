# Changelog

すべての重要な変更履歴をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-17
初回リリース

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - パッケージ公開対象モジュールを __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定管理 (kabusys.config)
  - .env / 環境変数から設定を自動読み込みする機能を実装。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に実行。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化に対応。
    - .env, .env.local を優先度に基づき読み込み（OS 環境変数は保護）。
  - .env のパースロジックを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - 必須環境変数取得ヘルパー `_require()` と Settings クラスを実装。以下のプロパティを提供：
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url
    - slack_bot_token, slack_channel_id
    - duckdb_path, sqlite_path
    - env, log_level とそれらのバリデーション (`development`, `paper_trading`, `live` / `DEBUG`〜`CRITICAL`)
    - is_live / is_paper / is_dev ヘルパー

- J-Quants クライアント (kabusys.data.jquants_client)
  - J-Quants API から日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダーを取得するクライアントを実装。
  - API レート制御: 固定間隔スロットリングで 120 req/min を守る RateLimiter 実装。
  - リトライロジック: 指数バックオフ（最大 3 回）、ステータスコード 408/429/5xx に対する再試行。
  - 401 Unauthorized を検知した場合、リフレッシュトークンで id_token を自動更新して 1 回リトライ。
  - id_token のモジュールレベルキャッシュを実装（ページネーション間で共有可能）。
  - ページネーション対応の取得関数を実装:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への冪等保存関数を実装:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - すべて ON CONFLICT（UPSERT）で重複を排除・更新
  - データ加工ユーティリティ: _to_float, _to_int（不正値や小数切り捨てを考慮）

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news テーブルへ保存するモジュールを実装。
  - セキュリティ・堅牢性対策:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト時のスキーム/プライベートアドレス検査（_SSRFBlockRedirectHandler）。
    - ホストがプライベート/ループバック等なら拒否（_is_private_host）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ削除（_normalize_url / _TRACKING_PARAM_PREFIXES）。
  - 記事IDは正規化 URL の SHA-256 ハッシュ先頭 32 文字で生成（_make_article_id）し冪等性を担保。
  - テキスト前処理（URL 除去、空白正規化）と RSS pubDate の安全なパース（_parse_rss_datetime）。
  - DB 保存の実装:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id で新規挿入 ID を取得。チャンク分割・1トランザクションで実行。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存、ON CONFLICT で重複をスキップ、INSERT ... RETURNING を用いて実際に挿入された件数を返す。
  - 銘柄コード抽出ロジック（4桁数字を候補とする正規表現）と既知銘柄セットによるフィルタ（extract_stock_codes）。
  - run_news_collection: 複数 RSS ソースを順次処理し、各ソースのエラーを独立して扱う統合ジョブを実装。既定の RSS ソースとして Yahoo Finance を登録。

- DuckDB スキーマ (kabusys.data.schema)
  - DataPlatform.md に沿った多層スキーマを定義・初期化するモジュールを実装。
  - Raw / Processed / Feature / Execution 層のテーブル定義を追加（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance など）。
  - 各種制約（PRIMARY KEY、CHECK 制約、FOREIGN KEY）を適用。
  - 頻出クエリ向けのインデックスを追加（例: idx_prices_daily_code_date, idx_signal_queue_status など）。
  - init_schema(db_path) でディレクトリ作成（必要時）、全 DDL / インデックスを実行して接続を返す。
  - get_connection(db_path) で既存 DB への接続を取得（スキーマ初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新／バックフィルを行う ETL パイプラインの基盤を実装。
  - ETLResult データクラスを追加（取得数・保存数・品質問題・エラーを集約）。
  - DB の最終取得日を確認するユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 取得対象日を営業日に調整するヘルパー（_adjust_to_trading_day）。market_calendar が未存在の場合はフォールバック。
  - run_prices_etl: 差分更新ロジック実装（最終取得日から backfill_days 分さかのぼって再取得するデフォルト挙動）、J-Quants クライアントとの連携。
  - 定数: 初回ロード用の最小日付 (_MIN_DATA_DATE = 2017-01-01)、カレンダー先読み日数、デフォルト backfill_days = 3、品質チェックの重大度識別子等。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- RSS パーサで defusedxml を使用し XML 攻撃を緩和。
- RSS/HTTP クライアントに対して SSRF 防止を実装（スキーム制限、リダイレクト先の事前検査、プライベート IP 検出）。
- HTTP レスポンスの読み込みに上限を設け、巨大レスポンスや Gzip 爆弾を防止。

### 互換性ブレーク (Breaking Changes)
- 初版のため該当なし。

---

注: 上記はコードベースから推測してまとめた初期リリースの主な変更点・特徴です。運用や API 仕様、DB スキーマの詳細（カラム名／型／制約）については実際のドキュメント（DataPlatform.md、API 仕様書等）を参照してください。