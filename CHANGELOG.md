# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog のガイドラインに準拠しています。  

全般:
- バージョンはパッケージの __version__（src/kabusys/__init__.py）に合わせています。
- 日付はリリース日を示します。

## [Unreleased]

### 注意 / 既知の問題
- run_prices_etl 関数の戻り値がコード末尾で不完全なまま（`return len(records), `）となっており、実行時に構文/戻り値の不整合を起こす可能性があります。リリース前に修正が必要です。
- その他、ユニットテストやエンドツーエンドテストでの検証が推奨されます（ネットワークやDB周りの外部依存が多いため）。

---

## [0.1.0] - 2026-03-18

### Added
- パッケージ骨格を導入（src/kabusys）
  - __version__ = 0.1.0 を設定。
  - パッケージの公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定・ローダー（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索）。
  - .env のパース処理を実装（export プレフィックス、クォート内エスケープ、インラインコメントの取り扱い等に対応）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須環境変数取得ヘルパー _require を実装。
  - Settings クラスを提供（J-Quants, kabuAPI, Slack, DBパス, 環境種別・ログレベルの検証メソッド等）。
  - 環境値検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）を実装。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務データ（四半期）、市場カレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - ID トークン取得とキャッシュ（get_id_token、モジュールレベルのトークンキャッシュ）。
  - レートリミッタ実装（120 req/min 固定間隔スロットリング）。
  - HTTP リクエストでのリトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
  - 401 時の自動トークンリフレッシュ（1 回のみ）を実装。
  - DuckDB への冪等保存関数（save_daily_quotes、save_financial_statements、save_market_calendar）を実装（ON CONFLICT DO UPDATE）。
  - レスポンスの JSON デコード失敗時のエラー処理、ログ出力を実装。
  - 型変換ユーティリティ (_to_float, _to_int) を実装（空値、非数値、安全な変換処理）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を取得し raw_news に保存する処理を実装。
  - セキュリティおよび堅牢性のための対策を多数導入：
    - defusedxml を使用して XML Bomb 等に対処。
    - SSRF 防止：URL スキーム検証、プライベートホスト判定（IP と DNS 解決による検査）、リダイレクト時の検査ハンドラ（_SSRFBlockRedirectHandler）。
    - レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後も上限検証。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保。
    - 公開ソースのデフォルト（DEFAULT_RSS_SOURCES: Yahoo Finance のカテゴリフィード）。
    - テキスト前処理（URL 除去、空白正規化）。
  - DB 書き込み処理:
    - save_raw_news: チャンク挿入 + INSERT ... RETURNING id を用いて新規挿入 ID を取得し返す。トランザクションでまとめて処理。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING, INSERT ... RETURNING により実際に挿入された件数を返す）。
  - 銘柄コード抽出ユーティリティ（4桁数字検出と known_codes による絞り込み）を実装。
  - run_news_collection: 複数ソースの収集を順次実行し、個々のソース失敗時はスキップして継続。既知銘柄コードが与えられた場合は紐付け処理を行う。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution レイヤごとのテーブル DDL を定義。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な制約（PRIMARY KEY、CHECK、FOREIGN KEY）を設定。
  - 頻出クエリ向けのインデックスを定義（例: idx_prices_daily_code_date 等）。
  - init_schema(db_path) でディレクトリ自動作成・DDL実行を行い、接続を返す（冪等）。
  - get_connection(db_path) で既存 DB への接続を返す（初期化は行わない）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETL 実行結果を表す ETLResult dataclass を提供（品質問題・エラー収集・シリアライズ用 to_dict を含む）。
  - 差分更新ユーティリティを実装:
    - テーブル存在チェック、最大日付取得の汎用関数（_table_exists, _get_max_date）。
    - 市場カレンダーに基づく営業日調整ヘルパー（_adjust_to_trading_day）。
    - raw_prices/raw_financials/market_calendar の最終取得日取得補助（get_last_price_date 等）。
  - run_prices_etl を実装（差分取得・backfill 日数設定、J-Quants からの取得→保存を実行）。
  - ETL 設計方針の実装（差分更新、backfill、品質チェックモジュールとの連携想定、id_token の注入可能性）。

### Security
- news_collector に SSRF 対策を導入（スキーム検証、ホストのプライベート判定、リダイレクト時検査）。
- defusedxml を採用し XML 関連の脆弱性を軽減。
- RSS フィードの応答サイズ制限と gzip 解凍後の上限検証を実装し、リソース消費攻撃を軽減。

### Changed
- （初期リリースのため変更履歴はなし）

### Fixed
- （初期リリースのため修正履歴はなし）

### Deprecated
- （初期リリースのためなし）

### Removed
- （初期リリースのためなし）

---

開発メモ:
- 外部 API / ネットワーク / DB に依存する機能が多いため、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って .env の自動ロードを抑制し、id_token や HTTP 呼び出しをモックすることを推奨します。
- run_prices_etl の戻り値不整合は早急に修正してください（ETL ワークフローでの呼び出し時に例外・不正な戻り値を招く可能性あり）。

もし CHANGELOG の表現や日付の変更、さらに詳細なリリースノート（例えばコマンド例、既知のマイグレーション手順など）を追加したい場合は指示してください。