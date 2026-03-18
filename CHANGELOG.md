Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。コードベースから推測できる変更点・機能をまとめています。必要なら日付や細かな表現を調整してください。

---
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠しています。  
安定版リリース、セキュリティ／互換性、重要な設計方針などを含めて記載しています。

Unreleased
----------

- なし

[0.1.0] - 2026-03-18
--------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージメタ情報: __version__ = "0.1.0"、公開モジュール: data, strategy, execution, monitoring

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を追加。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出: 現ファイル位置から上位に .git または pyproject.toml を探索して自動検出（CWD に依存しない）。
    - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサーの強化:
    - export KEY=val 形式をサポート
    - シングル／ダブルクォート内のエスケープ処理に対応
    - インラインコメントの扱い（クォート外かつ直前がスペース/タブの `#` をコメントとみなす）などのルールを実装
  - 環境設定ラッパー Settings を提供（プロパティ経由で必須値を取得）
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等の必須設定は未設定時に例外を発生
    - DuckDB/SQLite のデフォルトパス設定、環境（development/paper_trading/live）とログレベルのバリデーション、利便性プロパティ（is_live 等）

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しの共通処理とユーティリティを実装
    - ベース URL、レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）
    - 再試行戦略（最大3回、指数バックオフ、対象ステータス 408/429/5xx）
    - 401 発生時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ共有機能
    - JSON デコードのエラーハンドリング
  - 認証ヘルパー get_id_token を追加（リフレッシュトークンから ID トークンを取得）
  - データ取得 API: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - ON CONFLICT（UPSERT）を用いた冪等保存
    - fetched_at に UTC タイムスタンプを付与
    - PK 欠損行のスキップと警告ログ

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集して DuckDB に保存する ETL 機能を実装
    - デフォルト RSS ソース（例: Yahoo Finance のカテゴリフィード）
    - 記事IDは正規化した URL の SHA-256 の先頭 32 文字で生成（トラッキングパラメータ除去）
    - テキスト前処理（URL 除去・空白正規化）
    - defusedxml を利用した XML パース（XML Bomb 等への対策）
    - SSRF 対策:
      - URL スキーム検証（http/https のみ）
      - リダイレクト時にスキームとホスト（プライベート/ループバック/リンクローカル/マルチキャスト）を検査するカスタムリダイレクトハンドラ
      - 初回アクセス前のホスト事前検証（プライベートアドレスの拒否）
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）
    - DB への保存:
      - save_raw_news: INSERT ... RETURNING を用いて実際に挿入された記事 ID を返す（チャンク挿入、トランザクションまとめ）
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入、ON CONFLICT で重複スキップ
    - 銘柄抽出: 4 桁の銘柄コード抽出（既知コードとの突合せ、重複除去）

- DuckDB スキーマ定義 (kabusys.data.schema)
  - DataPlatform 設計に基づく多層スキーマを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの制約（PK、CHECK、FOREIGN KEY 等）を定義
  - 頻出クエリに対するインデックスを定義
  - init_schema(db_path) による初期化関数を提供（ディレクトリ自動作成、冪等実行）
  - get_connection(db_path) で既存 DB への接続を返す

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新／バックフィルを考慮した ETL ロジックの骨組みを実装
    - 最終取得日を基に自動で date_from を算出し、デフォルトの backfill_days=3 により後出し修正を吸収
    - 市場カレンダーの先読み（デフォルト lookahead を想定）
    - ETLResult dataclass を導入（取得件数・保存件数・品質問題・エラー要約を保持）、辞書化メソッドを提供
    - テーブル存在確認や最大日付取得のヘルパー関数（_table_exists, _get_max_date, get_last_price_date, ...）
    - 個別 ETL ジョブ: run_prices_etl を実装（差分計算、fetch + save の組み合わせ、ログ出力）

- モジュール構成
  - data, strategy, execution, monitoring のパッケージ骨組みを配置（__init__ が存在）

Security
- SSRF 対策を多数実装（URL スキーム検証、プライベート IP チェック、リダイレクト時検査）
- defusedxml の採用による XML 関連リスクの軽減
- レスポンスサイズ上限と gzip 解凍後の再チェック（DoS 対策）
- .env ロード時に OS 環境変数を保護する protected パラメータを導入（意図しない上書きを防止）

Performance / Reliability
- J-Quants クライアントにおけるレート制御とリトライ（指数バックオフ）で API 呼び出しの安定化
- DuckDB へのバルク挿入時にチャンク処理とトランザクションまとめを行いオーバーヘッドを低減
- 冪等性を意識した DB 保存（ON CONFLICT DO UPDATE / DO NOTHING）により再実行可能な ETL を実現

Notes / Migration
- 初回利用時は schema.init_schema(db_path) を呼び出してテーブルを作成してください（":memory:" のサポートあり）。
- 環境変数は .env / .env.local をプロジェクトルートに置くことで自動読み込みされます。CWD ではなくパッケージ位置からプロジェクトルートを判定します。
- KABUSYS_ENV と LOG_LEVEL は特定の値のみ受け付けます（バリデーションあり）。

Known issues / TODO
- pipeline.run_prices_etl などの ETL 関数は差分ロジックと保存処理の骨組みを実装済みですが、品質チェック（quality モジュール）や完全なバックフィル制御の統合、エラー詳細のハンドリング方針は今後の改善対象です（コードベースの設計コメント参照）。
- strategy / execution / monitoring パッケージは骨組みのみであり、具体的な戦略ロジック・発注実装・監視機能は今後追加予定。

---

ファイルやリリースノートの文言を調整したい場合、あるいは特定モジュール（例: news_collector / jquants_client / pipeline）の詳細な説明をリリースノートに追記したい場合は指示してください。