CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」準拠です。

[Unreleased]
------------

- （該当なし）

[0.1.0] - 2026-03-18
--------------------

初回公開リリース。

Added
- パッケージ基盤
  - パッケージバージョンを 0.1.0 としてリリース（src/kabusys/__init__.py）。
  - パッケージ公開 API: data, strategy, execution, monitoring をエクスポート。

- 設定管理
  - 環境変数/.env 自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から探索して .env と .env.local を読み込む（CWD に依存しない）。
    - 読み込みの無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で可能。
    - .env の行パースは export 句、クォート、インラインコメント、エスケープ等に対応。
    - OS 環境変数を保護する protected 上書きロジックを実装（.env.local は上書き可能だが OS 変数は保護）。
  - Settings クラスを提供し、必須値の取得 (例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD) や既定値（DUCKDB_PATH, SQLITE_PATH, KABU_API_BASE_URL）を管理。
  - KABUSYS_ENV / LOG_LEVEL の許容値検証を実装（不正な値は ValueError）。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py を追加。
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得機能（ページネーション対応）。
    - API レート制御: 固定間隔スロットリングで 120 req/min を尊重する RateLimiter を実装。
    - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx をリトライ対象に設定。429 の場合は Retry-After ヘッダ優先。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）を実装。トークン取得は get_id_token で POST。
    - JSON デコード失敗時の明確なエラーメッセージ出力。
    - データ保存用に DuckDB へ冪等的に挿入・更新する save_* 関数を提供（ON CONFLICT DO UPDATE）。
    - 保存時に fetched_at を UTC タイムスタンプで保存してデータ取得時刻をトレース可能に。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py を追加。
    - RSS フィード取得と記事正規化（title, content, url, pubDate の処理）。
    - defusedxml を用いた安全な XML パース（XML Bomb 等への対策）。
    - Gzip 圧縮対応と受信最大バイト数制限（デフォルト 10 MB）によるメモリ DoS 対策。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にスキームとホストを検査するカスタムリダイレクトハンドラ。
      - ホスト名/IP を解決してプライベート/ループバック/リンクローカル/マルチキャストを拒否。
      - 最終 URL に対する再検証。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ削除、フラグメント削除、クエリパラメータソート）。
    - 記事 ID は正規化 URL の SHA-256 の先頭32文字で一意化（冪等性確保）。
    - raw_news へチャンク単位で一括挿入し、INSERT ... RETURNING で実際に挿入された ID を返す。1 トランザクションでまとめてコミット/ロールバック。
    - 銘柄紐付け機能（news_symbols）を提供。重複除去、チャンク挿入、INSERT ... RETURNING により実際に挿入された件数を取得。
    - テキスト前処理（URL 除去、空白正規化）。
    - テキストから 4 桁銘柄コード抽出ロジック（既知コードセットとのマッチング）。

- DuckDB スキーマ定義
  - src/kabusys/data/schema.py を追加。
    - Raw / Processed / Feature / Execution の多層スキーマを定義し、init_schema(db_path) による初期化機能を提供。
    - 主要テーブル例: raw_prices, raw_financials, raw_news, market_calendar, prices_daily, features, ai_scores, signal_queue, orders, trades, positions, portfolio_performance 等。
    - 各テーブルに適切な型制約・CHECK・PRIMARY KEY を定義。
    - パフォーマンスを考慮したインデックス群を定義（頻出クエリ向け）。
    - DB ファイル親ディレクトリが存在しない場合は自動作成。":memory:" をサポート。

- ETL パイプライン
  - src/kabusys/data/pipeline.py を追加。
    - 差分更新ロジック（最終取得日を確認して未取得の範囲のみを取得）を実装。
    - backfill_days による再取得（デフォルト 3 日）で API の後出し修正を吸収。
    - 市場カレンダーの先読み設定（定数化）。
    - ETL 結果を表す ETLResult dataclass を導入（品質問題リスト・エラーリスト・集計値を保持）。
    - テーブル存在チェック、最大日付取得ユーティリティを実装。
    - run_prices_etl 等の個別 ETL 関数（差分取得、保存のワークフロー）を用意。
    - 品質チェック（quality モジュール想定）と連携する設計（品質問題は収集して ETL は継続する方針）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- ニュース収集における多数のセキュリティ対策を導入:
  - defusedxml による XML パース、安全なリダイレクト検査、プライベート IP の拒否、受信サイズ制限、gzip 解凍後のサイズ再検査など。
- 環境変数の自動読み込みで OS 環境変数を保護する protected ロジックを導入。

Notes / Migration
- 初期化:
  - DuckDB スキーマ初期化は init_schema(db_path) を呼び出してください（初回のみ）。
- 環境変数:
  - 必須環境変数が未設定の場合、Settings の該当プロパティは ValueError を投げます。リリース前に .env/環境変数を準備してください。
- ニュース収集:
  - デフォルト RSS ソースは Yahoo Finance のビジネスカテゴリ（DEFAULT_RSS_SOURCES）。必要に応じて run_news_collection に sources を渡してカスタマイズ可能です。
- API 利用:
  - J-Quants のトークン管理は Settings.jquants_refresh_token に依存します。API 率制限やリトライ挙動を考慮して運用してください。

ライセンス、貢献方法、詳細な設計ドキュメントは別途リポジトリ内のドキュメント（DataPlatform.md, DataSchema.md 等）を参照してください。