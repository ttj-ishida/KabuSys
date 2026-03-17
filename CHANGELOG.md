# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従い、セマンティックバージョニングを採用しています。

現行バージョン: 0.1.0

## [0.1.0] - 2026-03-17
初回公開リリース。

### Added
- パッケージの初期構成
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`、公開モジュール: `data`, `strategy`, `execution`, `monitoring` を __all__ に定義。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む `Settings` クラスを提供。以下の設定プロパティを実装:
    - J-Quants / kabuステーション / Slack / データベースパス / システム環境（env） / ログレベル 等
  - プロジェクトルート検出ロジックを実装（`.git` または `pyproject.toml` を基準）し、実行ディレクトリに依存しない自動 .env ロードを実現。
  - .env 解析ロジック: `export KEY=val` 形式、クォート処理、コメント処理をサポート。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用等に便利）。
  - 設定検証: `KABUSYS_ENV` と `LOG_LEVEL` の有効値チェック、未設定必須キーは `_require()` で明確な例外を送出。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 基本機能:
    - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得関数（ページネーション対応）を実装: `fetch_daily_quotes`, `fetch_financial_statements`, `fetch_market_calendar`。
    - 認証トークン取得: `get_id_token`（リフレッシュトークン -> idToken）。
  - 信頼性/運用面の設計:
    - グローバルな固定間隔レートリミッタで API レート制限（120 req/min）を順守。
    - リトライロジック（指数バックオフ、最大3回）。HTTP 408/429 と 5xx をリトライ対象に設定。429 の場合は `Retry-After` ヘッダを優先。
    - 401 受信時は自動でトークンをリフレッシュして1回だけリトライ（無限再帰防止）。
    - ページネーション間でトークンを共有するモジュールレベルキャッシュを実装。
  - DuckDB への保存関数（冪等性）:
    - `save_daily_quotes`, `save_financial_statements`, `save_market_calendar` により、ON CONFLICT DO UPDATE / DO NOTHING を用いた冪等保存を実現。
    - 保存時に取得時刻（UTC、fetched_at）を記録し、Look-ahead Bias の追跡をサポート。
  - ユーティリティ:
    - 型安全な変換関数 `_to_float`, `_to_int` を実装（不正値や小数部がある場合の扱いを明確化）。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードからのニュース収集フローを実装:
    - フィード取得、テキスト前処理（URL除去・空白正規化）、記事ID生成、DuckDB への冪等保存、銘柄コード紐付けまでをサポート。
  - セキュリティ・堅牢性対策:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストのプライベートアドレス判定、リダイレクト先検査用ハンドラ実装。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検証（Gzip bomb 対策）。
    - トラッキングパラメータ除去・URL 正規化、SHA-256（先頭32文字）で記事ID生成して冪等性を担保。
  - DB 操作:
    - `save_raw_news` はチャンク分割とトランザクションを用い、`INSERT ... ON CONFLICT DO NOTHING RETURNING id` により実際に挿入された ID を返却。
    - 複数記事の銘柄紐付けを一括で保存する `_save_news_symbols_bulk`、単一記事用の `save_news_symbols` を実装。
  - 銘柄コード抽出:
    - テキスト内の 4 桁数値パターンから既知銘柄セットに基づいて抽出する `extract_stock_codes` を実装。

- DuckDB スキーマ定義 & 初期化 (`kabusys.data.schema`)
  - DataPlatform.md に基づくスキーマを実装（Raw / Processed / Feature / Execution 層）。
  - テーブル定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 制約（PRIMARY KEY / CHECK / FOREIGN KEY）や INDEX の定義を含む。
  - `init_schema(db_path)` によりディレクトリ作成、スキーマ作成（冪等）と接続返却を実装。`:memory:` 対応。
  - `get_connection(db_path)` による既存 DB 接続取得を提供（初期化は行わない）。

- ETL パイプライン基盤 (`kabusys.data.pipeline`)
  - ETL の設計方針と実装の骨格:
    - 差分更新（DB の最終取得日を参照）、バックフィル（デフォルト 3 日）、市場カレンダー先読み（90日）等の方針を実装。
    - 結果を表現する `ETLResult` dataclass（品質チェックの結果とエラー集約、シリアライズ用 to_dict）を実装。
    - テーブル存在確認、最大日付取得ヘルパー（_table_exists, _get_max_date）を実装。
    - 非営業日調整ヘルパー `_adjust_to_trading_day`。
    - 差分ETL の一部（株価差分 ETL）を実装する `run_prices_etl`（最終取得日からの backfill 処理、fetch -> save の流れを実装）。
  - 品質チェック（外部モジュール quality との連携を想定）を統合する設計。

- その他
  - テスト容易性を考慮した抽象化（例: news_collector._urlopen を差し替え可能にしてモック可能にする等）。
  - 詳細なログ出力（info/warning/exception）を各処理に追加して運用性を向上。

### Notes
- 初期リリースのため、戦略（strategy）・実行（execution）・監視（monitoring）モジュールはパッケージとして準備されていますが（__all__ に含む）、それらの各サブパッケージはまだ実装の拡張余地があります。
- 一部の関数は内部設計（例: quality モジュール）や外部サービスの詳細（API トークンや DB スキーマとの運用）に依存します。導入時は `.env.example` を参考に適切な環境変数を設定してください。
- J-Quants API のレートやレスポンス仕様の変更、DuckDB の将来のバージョン互換性については運用で継続的に確認してください。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- RSS パースと HTTP 取得に関して複数の防御（defusedxml、SSRF 検査、受信サイズ制限、gzip 解凍検査）を実装しました。これらは外部の不正な入力に対する耐性を高める目的です。

---

今後のリリースでは、戦略モジュールの実装強化、発注/約定フローの統合、品質チェック（quality モジュール）との連携強化、テストカバレッジ拡充を予定しています。