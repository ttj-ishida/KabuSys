CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。
より詳細な設計や利用方法はソースコード内の docstring を参照してください。

記載方針
- 日付はリリース日時（本CHANGELOGはコードベースから推測して作成）。
- 可能な限りコードの実装内容から機能・改善点・セキュリティ対策等を列挙しています。

Unreleased
----------
（なし）

[0.1.0] - 2026-03-17
-------------------

Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システムのベース実装を追加。
  - パッケージバージョン: 0.1.0

- 基本パッケージ構成
  - モジュール構成: kabusys.{data,strategy,execution,monitoring}（strategy, execution, monitoring は初期プレースホルダ）。
  - __version__ によるバージョン管理を導入。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - 自動ロードの優先順: OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能（テスト等で利用）。
    - プロジェクトルート検出は __file__ を基点に .git または pyproject.toml を探索して行う（CWD に依存しない設計）。
  - .env のパース機能は export KEY=val、クォート、コメント、エスケープ等に対応。
  - 設定用 Settings クラスを提供（settings インスタンスを公開）。
    - J-Quants / kabu ステーション / Slack / DB パス / システム設定（KABUSYS_ENV, LOG_LEVEL）等のプロパティを用意。
    - 必須変数未設定時は明示的に ValueError を送出する _require 実装。
    - KABUSYS_ENV の許容値検証（development, paper_trading, live）。
    - LOG_LEVEL の許容値検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
    - デフォルト値: KABU_API_BASE_URL（http://localhost:18080/kabusapi）、DUCKDB_PATH/SQLITE_PATH。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 基本機能:
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
    - get_id_token によるリフレッシュトークン→IDトークン取得（POST）。
  - レート制御:
    - 固定間隔スロットリングによるレート制限（120 req/min、最小間隔 0.5 秒相当）。
  - 再試行（Retry）:
    - ネットワーク/HTTP失敗時のリトライ実装（最大 3 回、指数バックオフ）。
    - 408/429/5xx 系をリトライ対象。429 の場合は Retry-After ヘッダ優先。
  - 認証トークン管理:
    - モジュールレベルで ID トークンをキャッシュし、401 を受信した際は自動で1回トークンをリフレッシュして再試行（無限再帰防止）。
  - 取得データの保存（DuckDB 連携）:
    - save_daily_quotes / save_financial_statements / save_market_calendar を提供。
    - 保存は冪等性を担保（INSERT ... ON CONFLICT DO UPDATE）し、fetched_at を UTC タイムスタンプ（ISO 8601）で記録。
  - ユーティリティ:
    - 安全な型変換ヘルパー _to_float / _to_int（不正な値は None を返す）。
  - ロギング: 取得件数・保存件数・リトライやエラー発生時にログを出力。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news に保存する一連の処理を実装。
  - 主な機能・設計:
    - デフォルト RSS ソース（例: Yahoo Finance のビジネス RSS）。
    - RSS の取得 fetch_rss: XML のパース、title/description/content:encoded の取り扱い、pubDate パースを実装。
    - 記事ID は URL 正規化後の SHA-256（先頭32文字）で生成して冪等性を担保（utm_* 等のトラッキングパラメータ削除、クエリパラメータソート、フラグメント削除）。
    - テキスト前処理（URL 除去、空白正規化）。
    - Save ロジック:
      - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、実際に挿入された記事IDのみを返却。全操作を1トランザクションで行い失敗時はロールバック。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをバルク挿入（ON CONFLICT DO NOTHING）で行い、挿入件数を正確に返す。
    - 銘柄コード抽出: 4桁数字パターンを検出し、known_codes に含まれるもののみを採用、重複は除去。
  - 安全性対策:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - SSRF 対策:
      - リダイレクトハンドラでリダイレクト先のスキームとホストが許可範囲かを検証。
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストアドレスの場合は拒否（直接 IP または DNS 解決による判定）。
      - URL スキームは http/https のみ許可。
    - レスポンスサイズ制限（最大 10 MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - HTTP ヘッダの Content-Length を事前チェック（不正値は無視して挙動を安全側に）。
  - 統合ジョブ:
    - run_news_collection: 複数ソースを順次処理し、ソース単位でエラーハンドリング（1ソース失敗でも他ソース継続）。新規保存数を集計して返す。

- DuckDB スキーマ管理（kabusys.data.schema）
  - DataSchema に基づく DuckDB の DDL を実装。init_schema(db_path) でテーブル群・インデックスを作成して接続を返す。
  - Raw / Processed / Feature / Execution の4層構造テーブルを定義（主なテーブル一覧）:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 主キー・外部キー・CHECK 制約によりデータ整合性を確保（例: side が 'buy'/'sell'、size > 0、price >= 0 等）。
  - 検索性能を考慮したインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status など）。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETL の基本方針とユーティリティ実装:
    - 差分更新のための最終取得日取得ユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 市場カレンダーに基づく取引日調整ヘルパー (_adjust_to_trading_day)。
    - ETLResult データクラス: ETL 実行結果の集計、品質チェック結果の集約、エラーフラグの判定 (has_errors, has_quality_errors)。
    - run_prices_etl の部分実装:
      - 差分更新ロジック（date_from が未指定の場合は DB の最終取得日 - backfill_days を自動算出）。
      - backfill_days のデフォルトは 3 日（API の後出し修正を吸収する戦略）。
      - J-Quants からの取得と保存の呼び出し（jq.fetch_daily_quotes → jq.save_daily_quotes）。
    - 定数: J-Quants 利用開始日（2017-01-01）、カレンダー先読み日数（90 日）等。
  - 品質チェックモジュール（quality）との連携を想定（quality.QualityIssue を用いる設計）。

Security
- 認証情報の取り扱いと自動ロード:
  - 必須の機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は Settings で必須として検証。未設定時は明示的なエラーを出す。
  - .env 読み込み時に OS 環境変数を上書きしない（デフォルト）かつ .env.local で上書き可。既存の OS 環境変数を保護する protected 機構を実装。
- 外部ネットワークリソース取り扱いの安全対策（主に news_collector）:
  - SSRF 対策、スキーム検証、プライベートIP/ホスト検出、XML パースのセーフ実装、レスポンスサイズ上限、gzip 解凍後サイズ検査等を実施。

Notes / Usage
- DuckDB の初期化:
  - 初回は kabusys.data.schema.init_schema(db_path) を呼び出して DB を作成・スキーマ初期化してください。
  - get_connection は既存 DB へ接続する際に使用。
- 環境変数の自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- J-Quants API はレート上限（120 req/min）と再試行ポリシーに従ってアクセスされます。大規模なバックフィル時はこの制約に注意してください。
- news_collector.fetch_rss は URL のスキームとホストの検証を厳格に行うため、内部ホストや非 http/https スキームのフィードは取得されません。

Known limitations / TODO
- strategy, execution, monitoring の具体実装はプレースホルダ（未実装）。
- pipeline.run_prices_etl はファイル末尾の切り取りによりサンプルの一部が途中で終わっている可能性がある（実運用向けには更なる機能（品質チェック呼び出し、calendar の前後取得等）が必要）。
- ロギング/メトリクスの集約や詳細なエラーハンドリング、テストカバレッジの整備は今後の改善対象。

ライセンス・依存
- DuckDB を DB エンジンとして使用（duckdb Python パッケージ必須）。
- RSS の安全パースに defusedxml を使用。
- ネットワーク I/O は urllib を利用（本実装では urllib.request を直接使用）。

----- End of CHANGELOG -----