Keep a Changelog に準拠した CHANGELOG.md

すべての変更点は意図的にコードから推測して記載しています。

## [Unreleased]
- 今後の変更点をここに記載します。

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買プラットフォーム "KabuSys" の基盤機能を追加。

### 追加 (Added)
- パッケージ基礎
  - パッケージバージョンを 0.1.0 として公開。
  - kabusys の公開モジュール: data, strategy, execution, monitoring を定義。

- 環境設定 (kabusys.config)
  - .env ファイルおよび環境変数からの設定自動読み込み機能を実装。
    - ルート検出は .git または pyproject.toml を起点に行い、CWD に依存しない挙動。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート・バックスラッシュエスケープの扱い、インラインコメント処理などに対応）。
  - Settings クラスを提供し、必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）や既定値（KABU_API_BASE_URL, DUCKDB_PATH 等）、KABUSYS_ENV/LOG_LEVEL 値検証、is_live / is_paper / is_dev 補助プロパティを実装。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日足（OHLCV）、財務諸表（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* API を実装。
  - レートリミッタ（120 req/min 固定間隔スロットリング）を実装して API レート制限を保護。
  - リトライロジック（指数バックオフ、最大 3 回）。408/429/5xx をリトライ対象に。
  - 401 受信時はリフレッシュトークンから id_token を自動更新して 1 回リトライする仕組みを実装（無限再帰防止）。
  - ページネーション対応（pagination_key の循環防止）。
  - DuckDB へ保存する save_* 関数を実装（idempotent な INSERT ... ON CONFLICT DO UPDATE）。
  - データ取得時に fetched_at を UTC タイムスタンプで付与し、Look-ahead Bias を抑止。
  - 型変換ユーティリティ (_to_float / _to_int) を提供（安全な変換と None 処理）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュースを収集し raw_news / news_symbols に保存する一連の機能を実装。
  - 主要機能:
    - fetch_rss: RSS 取得、XML パース（defusedxml 使用）と記事抽出（title, content, pubDate の正規化）。
    - URL 正規化とトラッキングパラメータ除去（_normalize_url, _make_article_id: SHA-256 の先頭32文字）。
    - SSRF 対策: 非 http/https スキーム拒否、ホストがプライベート/ループバックである場合は拒否、リダイレクト時の事前検査ハンドラ実装。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）や gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - テキスト前処理（URL 除去、空白正規化）。
    - save_raw_news / save_news_symbols / _save_news_symbols_bulk: DuckDB へのチャンク挿入、トランザクション制御、ON CONFLICT DO NOTHING と INSERT ... RETURNING による正確な挿入数取得。
    - 銘柄コード抽出 (extract_stock_codes): テキスト中の 4 桁数字を検出して既知銘柄セットと突合。
    - run_news_collection: 複数 RSS ソースの収集ジョブを統合。ソース単位で独立したエラーハンドリングを実施し、銘柄紐付けをバルクで行う。

- スキーマ定義 (kabusys.data.schema)
  - DuckDB 用の完全なスキーマ（Raw / Processed / Feature / Execution レイヤ）を定義。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な型・制約（NOT NULL、CHECK、PRIMARY KEY、FOREIGN KEY）を設定。
  - インデックス定義（頻出クエリパターンに基づく）。
  - init_schema(db_path) でディレクトリ作成とテーブル/インデックスの作成を行い、get_connection 関数で接続を取得可能。

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult データクラスで ETL 実行結果（取得数、保存数、品質問題、エラー）を管理。
  - 差分更新ヘルパー（テーブルの最終日付取得 get_last_price_date / get_last_financial_date / get_last_calendar_date）。
  - 取引日調整ヘルパー (_adjust_to_trading_day)。
  - run_prices_etl: 差分更新ロジック（最終取得日から backfill_days を考慮して再取得）、API 取得→保存の一連処理を実装。バックフィルデフォルトは 3 日。
  - パイプライン設計は品質チェックモジュール (quality) と連携する想定（品質チェックは ETL 中に問題を報告しても処理継続する設計）。

### 変更点 (Changed)
- （初回リリースにつき該当なし）

### 修正 (Fixed)
- （初回リリースにつき該当なし）

### セキュリティ (Security)
- ニュース収集において SSRF 対策を導入（スキーム検証、プライベートアドレス判定、リダイレクト先検査）。
- XML 解析に defusedxml を使用して XML Bomb や外部エンティティ攻撃を防止。
- 外部リソースからの受信サイズ上限を設け、メモリ DoS を軽減。

### 既知の制約 / メモ
- Settings は必須環境変数が未設定の場合に ValueError を送出するため、実行前に .env または環境変数の設定が必要。
- jquants_client のレート制限は固定間隔スロットリングを採用しているため、短時間での突発的なバーストには注意が必要。
- pipeline モジュールでは quality モジュールの実装に依存する箇所がある（品質チェックは外部モジュールにより詳細制御される想定）。
- DuckDB のスキーマは初期化時に既存テーブルがあればスキップする（冪等性）。

---
今後のリリースでは、strategy / execution / monitoring 向けの実戦運用ロジック（シグナル生成、注文送信、SLACK 通知、監視ダッシュボード等）やテスト・CI 設定、ドキュメント追補を予定してください。