# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはリポジトリの現状のコードベースから推測して作成しています。

現在のバージョン: 0.1.0

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-17

初期リリース。本プロジェクト「KabuSys」の基本的なコンポーネントを実装しました。主な追加点は以下の通りです。

### Added
- 基本パッケージ定義
  - パッケージメタ情報を追加（src/kabusys/__init__.py、__version__ = "0.1.0"）。
  - public API として data, strategy, execution, monitoring をエクスポート。

- 環境設定モジュール（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
    - プロジェクトルートは __file__ を基点に `.git` または `pyproject.toml` で探索（CWD 非依存）。
  - .env パーサを実装（コメント/export 形式、シングル/ダブルクォート、エスケープ処理、インラインコメント対応）。
  - 必須設定取得ヘルパー `_require()` と Settings クラスを提供。
  - サポートされる設定:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
  - Settings に便利なプロパティ（is_live/is_paper/is_dev）を追加。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 基本機能:
    - 日次株価（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得する関数を実装（ページネーション対応）。
  - 信頼性と安全性:
    - 固定間隔スロットリングによるレート制限（120 req/min）を厳守する RateLimiter。
    - リトライロジック（指数バックオフ、最大 3 回）。再試行対象は 408/429/5xx。
    - 401 Unauthorized 受信時はリフレッシュトークンで id_token を自動更新して最大 1 回リトライ（無限再帰防止のため allow_refresh 制御）。
    - モジュールレベルの id_token キャッシュによりページネーション間でトークンを共有。
  - データ保存:
    - DuckDB に対する保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。
    - 冪等性を担保するため ON CONFLICT DO UPDATE を使用。
    - fetched_at を UTC で記録して「いつデータを知り得たか」をトレース可能に。
  - ユーティリティ:
    - 型変換ヘルパー _to_float / _to_int（堅牢な変換・None 処理）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を取得し DuckDB の raw_news に保存するワークフローを実装。
  - 設計上の特徴:
    - defusedxml を使用した安全な XML パース（XML Bomb 等の防御）。
    - SSRF 対策:
      - URL スキーム制限（http/https のみ）。
      - リダイレクト時のスキーム・ホスト検証（内部アドレス判定）。
      - ホスト名の DNS 解決後の IP 判定（プライベート/ループバック/リンクローカル/マルチキャストを拒否）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）。Gzip 解凍後サイズチェックも実装（Gzip Bomb 対策）。
    - URL 正規化:
      - スキーム/ホスト小文字化、トラッキングパラメータ（utm_ など）除去、フラグメント削除、クエリパラメータソート。
      - 記事ID は正規化 URL の SHA-256（先頭32文字）を採用し冪等性を担保。
    - テキスト前処理（URL 除去、空白正規化）。
  - DB 保存:
    - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id で新規挿入 ID を正確に取得、トランザクションでまとめてコミット/ロールバック処理。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（ON CONFLICT DO NOTHING RETURNING で実際の挿入数を取得）。
  - 銘柄コード抽出:
    - 4桁数字パターンで候補を抽出し、既知銘柄セットによるフィルタを適用（重複除去）。
  - run_news_collection: 複数ソースからの収集を行う統合ジョブ（各ソースは個別にエラーハンドリング、known_codes による紐付けオプションあり）。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを設定。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - DataSchema.md 想定に基づく 3 層＋実行層のテーブル群を定義（DDL を冪等で実行）。
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約・チェック（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）を含む設計。
  - インデックス定義（頻出クエリに備えたインデックスを作成）。
  - init_schema(db_path) と get_connection(db_path) を提供。init_schema は親ディレクトリ自動作成（file system）を行う。

- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - ETLResult dataclass により ETL 実行結果を構造化（品質問題、エラー一覧、各種カウント）。
  - 差分更新ロジック:
    - raw テーブルの最終取得日を取得して差分のみを取得（デフォルトバックフィルは 3 日）するヘルパー。
    - 市場カレンダーの先読み（lookahead）や取引日調整ヘルパーを実装。
  - run_prices_etl を実装（対象期間の差分取得 → jquants_client 経由で取得 → save ）。品質チェックモジュールとの連携ポイントを想定。
  - 汎用ユーティリティ: テーブル存在チェック、日付最大値取得。

### Security
- RSS パーシングで defusedxml を導入し、XML 関連攻撃に対する防御を強化。
- ニュース収集で SSRF 対策（スキーム検証、プライベート IP 判定、リダイレクト検査）を強化。
- .env 読み込みで OS 環境変数の上書きを制御する protected セットを導入。

### Notes / 注意点
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings により未設定時に ValueError を送出します。デプロイ前に .env または環境変数を設定してください。
- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml）を基に .env/.env.local を自動ロードします。ライブラリ利用時に自動読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- レート制限:
  - J-Quants API は 120 req/min を想定。クライアントは固定間隔スロットリングでこれを守る設計です。
- データのタイムスタンプ:
  - fetched_at は UTC タイムゾーンで記録されます（Z 形式）。これにより Look-ahead Bias のトレースが可能です。

### Known issues / TODO（コードからの推測）
- run_prices_etl の戻り値がファイル末尾で未完成のように見えます（ソース末尾で `return len(records),` とだけなっており、保存件数を含むべきところが欠けている）。本番利用前にこの戻り値と呼び出し側の期待値を確認・修正する必要があります。
- strategy/ execution/ monitoring の各パッケージは __init__ が存在するものの、現状で実装は見当たりません。戦略実装・発注ロジック・監視機能は今後の実装対象です。
- schema の FOREIGN KEY 制約や DuckDB のバージョン差異により一部振る舞いが異なる可能性があるため、実環境でのスキーママイグレーション確認を推奨します。

---

この CHANGELOG はコードベースの実装内容を元に推測して作成しています。実際のリリースノートとして使用する場合は、コミット履歴・PR・リリース差分を参照の上、必要に応じて修正してください。