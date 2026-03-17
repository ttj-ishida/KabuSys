CHANGELOG
=========

すべての注目すべき変更を時系列で記録します。  
このファイルは Keep a Changelog の書式に準拠します。

バージョン付け: Semantic Versioning に準拠します。

[Unreleased]
------------

（現在のスナップショットではリリース済みの最初のバージョン 0.1.0 を含みます）

0.1.0 - 2026-03-17
------------------

初回公開リリース。日本株自動売買プラットフォームの基盤機能を実装しました。主な追加点は以下のとおりです。

Added
- パッケージ情報
  - kabusys パッケージを導入。バージョンは __version__ = "0.1.0"、パブリック API として data, strategy, execution, monitoring をエクスポート。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数からの設定値読み込みを実装。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に __file__ を起点に親ディレクトリ探索（CWD 非依存）。
  - .env の行パーサ: export KEY=val 形式、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 自動ロードの優先順位: OS 環境 > .env.local > .env。OS 環境変数は保護（上書き禁止）。
  - 自動ロード無効化オプション: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - Settings クラスを提供し、J-Quants トークン、kabu API 設定、Slack トークン/チャンネル、DB パス（duckdb/sqlite）、実行環境（development/paper_trading/live）、ログレベル等をプロパティとして取得・バリデーション。

- J-Quants クライアント（kabusys.data.jquants_client）
  - API ベース実装: 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX 市場カレンダーの取得機能。
  - レート制限: 固定間隔スロットリングで 120 req/min を遵守（_RateLimiter）。
  - リトライ戦略: 指数バックオフ（base=2.0 秒）と最大試行回数 3、HTTP 408/429 と 5xx をリトライ対象。
  - 401 Unauthorized の自動リフレッシュ: トークン期限切れ検出時にリフレッシュを 1 回行ってリトライ（無限再帰回避）。
  - id_token キャッシュ（モジュールレベル）によりページネーション間でトークンを共有。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements）、単一取得の fetch_market_calendar。
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT DO UPDATE を利用して重複・更新を扱う。
  - レスポンス JSON デコード・エラーハンドリング、ログ出力。
  - 数値変換ユーティリティ (_to_float, _to_int) を追加（安全な型変換、空値ハンドリング）。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news に保存する機能を実装。
  - セキュリティ対策:
    - defusedxml を使用した XML パース（XML Bomb 等の防御）。
    - SSRF 対策: 許可スキームは http/https のみ、ホストがプライベート/ループバック/リンクローカル/マルチキャストでないことを DNS 解決・IPチェックで検査。リダイレクト時も検査するカスタム RedirectHandler を導入。
    - 受信サイズ上限: MAX_RESPONSE_BYTES = 10MB（事前 Content-Length と読み込みバイト数でチェック）、gzip 解凍後も上限チェック。
  - URL 正規化: 小文字化、トラッキングパラメータ（utm_*, fbclid, gclid 等）除去、フラグメント削除、クエリをキーでソート。
  - 記事 ID 生成: 正規化 URL の SHA-256（先頭 32 文字）を使用して冪等性を担保。
  - テキスト前処理: URL 除去、空白正規化。
  - DB 保存: DuckDB へのチャンク INSERT（_INSERT_CHUNK_SIZE、デフォルト 1000）を実装。INSERT ... ON CONFLICT DO NOTHING RETURNING を使い実際に挿入された ID を返却（save_raw_news）。
  - 銘柄紐付け機能: テキストから 4 桁銘柄コードを抽出して news_symbols に保存（extract_stock_codes, save_news_symbols, _save_news_symbols_bulk）。重複除去・トランザクションで一括保存。

- DuckDB スキーマ定義（kabusys.data.schema）
  - DataPlatform.md に基づくレイヤードスキーマを実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに型・CHECK 制約・PRIMARY KEY・FOREIGN KEY を定義。
  - インデックス定義（頻出クエリ向け）を多数追加。
  - init_schema(db_path) でディレクトリ作成 → 接続 → テーブル作成を行う冪等初期化を提供。get_connection(db_path) で既存 DB へ接続。

- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETLResult dataclass により ETL 実行結果（取得数/保存数/品質問題/エラー）を表現。
  - 差分取得ユーティリティ: テーブルの最終取得日を取得する get_last_* 関数群。
  - 市場カレンダー補助: 非営業日の場合に直近営業日に調整する _adjust_to_trading_day。
  - run_prices_etl 実装（差分更新、バックフィル機能）:
    - デフォルトバックフィル: 3 日（後出し修正吸収のため）。
    - データ開始日は 2017-01-01（初回ロード用）。
    - J-Quants クライアントを用いて差分を fetch → save。取得件数と保存件数を返す設計。
  - ETL 設計方針: 品質チェック（quality モジュール）を統合予定。Fail-fast ではなく収集を継続し呼び出し元に判断を委ねる。

Changed
- （初回リリースのためなし）

Fixed
- （初回リリースのためなし）

Security
- ニュース収集に関するセキュリティ対策を多数実装（SSRF 防御・XML パース防御・受信サイズ制限・URL スキーム検証など）。
- .env 読み込みにおいて OS 環境変数を保護し、意図しない上書きを防止。

Known Issues / Notes
- run_prices_etl の実装に関して型シグネチャと戻り値（tuple[int, int]）の不整合が確認されます。現在の実装（コード末尾）は return len(records), と単一要素のタプル（または意図しない途中終了）になっており、呼び出し側が (fetched, saved) の 2 値を期待する場合に問題となります。保存数（saved）を返す実装に修正が必要です。
- pipeline モジュールは quality モジュールに依存していますが（品質チェック）、提供されたスニペット内に quality の実装は含まれていません。品質チェックの具体的なルールは別モジュールで実装する想定です。
- strategy, execution, monitoring の各パッケージは __all__ に含まれていますが、スニペット内では中身が空（__init__.py が空）です。各レイヤーの実装は今後追加される想定です。

Upgrade Notes
- 既存の環境で .env 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマ初期化は init_schema() を使って行ってください。既存テーブルがあればスキップされるため安全に実行できます。

謝辞 / 備考
- 本リポジトリの初回リリースでは外部 API（J-Quants）や DuckDB との連携、RSS 処理など基盤的な実装に注力しました。以降のリリースで戦略実装（strategy）、注文発注ロジック（execution）、監視（monitoring）、品質チェック（quality）の細部を充実させる予定です。