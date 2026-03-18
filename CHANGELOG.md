CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョン番号はパッケージ内の __version__ に合わせています。

[0.1.0] - 2026-03-18
-------------------

Added
- 初期リリース。日本株自動売買プラットフォームの基盤機能を提供するモジュール群を追加。
  - パッケージエントリポイント
    - kabusys.__init__: パッケージバージョンと公開サブモジュール (data, strategy, execution, monitoring) を公開。
  - 設定/環境管理
    - kabusys.config:
      - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml で検出）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
      - .env のパースは export 形式、クォート付き値、インラインコメント等に対応。
      - settings オブジェクトでアプリ設定（JQUANTS_REFRESH_TOKEN 等必須設定、DB パス、環境モード、ログレベル等）をプロパティで提供。
  - J-Quants API クライアント
    - kabusys.data.jquants_client:
      - API レート制御（120 req/min）を固定間隔スロットリングで実装。
      - リトライ戦略（指数バックオフ、最大 3 回、408/429/5xx を再試行対象）。
      - 401 応答時にはリフレッシュトークンで id_token を自動更新し 1 回リトライ。
      - ページネーション対応のデータ取得関数:
        - fetch_daily_quotes（OHLCV）
        - fetch_financial_statements（四半期財務）
        - fetch_market_calendar（JPX カレンダー）
      - データベース保存関数（DuckDB）で冪等性を確保（ON CONFLICT DO UPDATE）:
        - save_daily_quotes, save_financial_statements, save_market_calendar
      - レスポンス取得時に fetched_at を UTC で記録して Look-ahead バイアスを抑制。
  - ニュース収集
    - kabusys.data.news_collector:
      - RSS フィード収集と前処理パイプラインを実装（デフォルトで Yahoo Finance RSS を含む）。
      - defusedxml を用いた XML パースで XML Bomb 等の攻撃を軽減。
      - SSRF 対策:
        - リダイレクト先のスキーム検証・プライベートアドレス検出（DNS 解決 + IP 判定）。
        - HTTP/HTTPS 以外のスキーム拒否。
      - レスポンスボディサイズ制限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後も検査。
      - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）。
      - 記事ID は正規化 URL の SHA-256 の先頭 32 文字で生成し冪等性を保証。
      - DB 保存はチャンク化した INSERT ... RETURNING を利用し、挿入された新規 ID を返す（save_raw_news, save_news_symbols）。
      - 銘柄コード抽出ロジック（4桁数字パターン）と bulk 保存補助。
  - DuckDB スキーマ定義・初期化
    - kabusys.data.schema:
      - Raw / Processed / Feature / Execution 層を包含するテーブル群を定義（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, features, ai_scores, signals, orders, trades, positions 等）。
      - インデックス定義とテーブル作成順を考慮した init_schema(db_path) を実装。親ディレクトリ自動作成対応。
      - get_connection(db_path) で既存 DB への接続を提供。
  - ETL パイプライン骨子
    - kabusys.data.pipeline:
      - ETLResult データクラスにより ETL 実行結果（取得数・保存数・品質問題・エラー等）を表現。
      - 差分更新のヘルパー（テーブル存在確認、最大日付取得、営業日調整）。
      - run_prices_etl 実装（差分取得ロジック、バックフィル日数処理、jquants_client 経由で取得→保存）。バックフィルや最小データ日付等の定数を設定。
      - 品質チェック（quality モジュールを参照する設計）を呼び出すための拡張点を用意。

Security
- ニュース収集で SSRF 対策や defusedxml を導入。外部 URL の検証、プライベートネットワークへのアクセス防止、受信サイズ制限などを実装。

Notes / ユーザー向けマイグレーション / 使用上の注意
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - これらが未設定の場合、settings の該当プロパティ呼び出しで ValueError が発生します。
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH を変更可能）
  - SQLite（monitoring 用）: data/monitoring.db（環境変数 SQLITE_PATH）
- 自動 .env 読み込み:
  - OS 環境変数 > .env.local > .env の優先順位でロード。OS 環境を上書きしたくない場合は .env を使うか KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- ETL 実行:
  - 初回は schema.init_schema() で DB を作成してから ETL を実行してください。
  - run_prices_etl は差分取得を行い、backfill により最終取得日の数日前から再取得して API の後出し修正を吸収します。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Known Issues / 今後の改善予定
- pipeline モジュールは Prices の ETL ジョブの流れを実装済みだが、財務データ・カレンダーの完全な ETL フローや品質チェックの統合（quality モジュールとの連携点）については今後の実装／拡張が想定されます。
- strategy / execution / monitoring パッケージの詳細実装はこれから追加される想定（現時点でパッケージは存在するが中身は未実装または外部実装を想定）。

-- End of CHANGELOG --